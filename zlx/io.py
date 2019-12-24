from __future__ import absolute_import
import sys
import io
import threading
import time
from collections import namedtuple

import zlx.int
import zlx.record

from zlx.utils import sfmt, dmsg, omsg, emsg

SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2
SEEK_DATA = 3
SEEK_HOLE = 4

def bin_load (path):
    with open(path, 'rb') as f:
        return f.read()

def bin_save (path, content):
    with open(path, 'wb') as f:
        return f.write(content)

def txt_load (path):
    with open(path, 'r') as f:
        return f.read()

def txt_save (path, content):
    with open(path, 'w') as f:
        return f.write(content)

class chunk (object):
    __slots__ = 'stream offset size'.split()
    def __init__ (self, stream, offset, size):
        self.stream = stream
        self.offset = offset
        self.size = size

class chunked_stream (io.RawIOBase):

    def __init__ (self, io_chunks):
        self.io_chunks = tuple(io_chunks)
        self.chunk_pos = []
        pos = 0
        for c in self.io_chunks:
            self.chunk_pos.append(pos)
            pos += c.size
        self.size = pos
        self.chunk_pos.append(pos)
        self.pos = 0

    def seekable (self):
        return True

    def seek (self, offset, whence=SEEK_SET):
        if whence == SEEK_SET: pass
        elif whence == SEEK_CUR: offset += self.pos
        elif whence == SEEK_END: offset += self.size
        else: raise ValueError('unsupported whence {}'.format(whence))
        if offset < 0: raise ValueError('negative offset')
        self.pos = offset
        return offset

    def offset_to_chunk_index (self, offset):
        a, b = 0, len(self.io_chunks) - 1
        while a <= b:
            c = (a + b) // 2
            if offset >= self.chunk_pos[c]:
                if offset < self.chunk_pos[c + 1]:
                    return c
                a = c + 1
            else:
                b = c - 1
        return None

    def readinto (self, b):
        size = len(b)
        #print('readinto pos={} size={}'.format(self.pos, size))
        out_ofs = 0
        while out_ofs < size:
            cx = self.offset_to_chunk_index(self.pos)
            if cx is None: break
            offset_in_chunk = self.pos - self.chunk_pos[cx]
            cplen = min(size - out_ofs, self.io_chunks[cx].size - offset_in_chunk)
            #print('cx={} oic={} seekpos={} cplen={}'.format(cx, self.io_chunks[cx].offset + offset_in_chunk, self.io_chunks[cx].offset + offset_in_chunk, cplen))
            self.io_chunks[cx].stream.seek(self.io_chunks[cx].offset + offset_in_chunk)
            #print('before data={!r}'.format(b[out_ofs:out_ofs + cplen]))
            data = self.io_chunks[cx].stream.read(cplen)
            n = len(data)
            b[out_ofs:out_ofs + n] = data
            #print('n={} data={!r}'.format(n, b[out_ofs:out_ofs + cplen]))
            out_ofs += n
            self.pos += n
            if n != cplen: break
        return out_ofs

class ba_view (io.RawIOBase):
    '''
    Creates a stream backed by an existing bytearray-like object.
    '''
    __slots__ = 'ba pos'.split()
    def __init__ (self, ba):
        self.ba = ba
        self.pos = 0
    def seekable (self): return True
    def seek (self, offset, whence = SEEK_SET):
        if whence == SEEK_SET: pass
        elif whence == SEEK_CUR: offset += self.pos
        elif whence == SEEK_END: offset += len(self.ba)
        else: raise ValueError('unsupported whence {}'.format(whence))
        if offset < 0: raise ValueError('negative offset')
        self.pos = offset
        return offset
    def readinto (self, b):
        cplen = min(len(b), len(self.ba) - self.pos)
        if cplen <= 0: return None
        b[0:cplen] = self.ba[self.pos : self.pos + cplen]
        return cplen
    def __len__ (self):
        return len(self.ba)

#/* stream_cache *************************************************************/
SCK_UNCACHED = 0
SCK_CACHED = 1
SCK_HOLE = 2

class uncached_data_block (zlx.record.Record):
    __slots__ = 'offset size'.split()
    kind = SCK_UNCACHED
    _field_repr = {}
    def get_size (self): return self.size
    def desc (x): return sfmt('uncached(0x{:X},0x{:X})', x.offset, x.size)
    def __repr__ (self): return self.desc()

class cached_data_block (zlx.record.Record):
    __slots__ = 'offset data'.split()
    kind = SCK_CACHED
    _field_repr = {}
    def get_size (self): return len(self.data)
    def desc (x): return sfmt('cached(0x{:X},0x{:X},{!r})', x.offset, len(x.data), bytes(x.data[0:4]))
    def __repr__ (self): return self.desc()

class hole_block (zlx.record.Record):
    __slots__ = 'offset size'.split()
    kind = SCK_HOLE
    _field_repr = {}
    def get_size (self): return self.size
    def desc (x):
        if x.size:
            return sfmt('hole(0x{:X},0x{:X})', x.offset, x.size)
        else:
            return sfmt('end(0x{:X})', x.offset)
    def __repr__ (self): return self.desc()

#/* stream_cache_base ********************************************************/
class stream_cache_base (object):

    def __init__ (self):
        object.__init__(self)

    def get (self, offset, size):
        '''
        returns a list of blocks that describe the given range as returned
        by get_part()
        '''
        a = []
        while size:
            blk = self.get_part(offset, size)
            a.append(blk)
            offset += blk.get_size()
            size -= blk.get_size() or size
        return a

#/* stream_cache *************************************************************/
class stream_cache (stream_cache_base):

    def __init__ (self, stream, align = 4096, assume_size = None):

        stream_cache_base.__init__(self)
        self.stream = stream

        self.seekable = False
        self.blocks = []

        if assume_size is not None:
            self.seekable = stream.seekable()
            end = assume_size
        elif stream.seekable():
            try:
                self.pos = stream.seek(0, SEEK_CUR)
                end = stream.seek(0, SEEK_END)
                stream.seek(self.pos, SEEK_CUR)
                self.seekable = True
            except:
                pass
        if self.seekable:
            if end > 0:
                self.blocks.append(uncached_data_block(0, end))
            self.blocks.append(hole_block(end, 0))
            assert zlx.int.pow2_check(align), "alignment must be a power of 2"
            self.align = align # alignment for offsets / sizes when doing I/O
        else:
            self.blocks.append(hole_block(0, 0))
            self.align = 1

    def __repr__ (self):
        return sfmt('stream_cache(stream={!r}, seekable={!r}, blocks=[\n    {}])', self.stream, self.seekable, '\n    '.join([x.desc() for x in self.blocks]))

    def locate_block (self, offset):
        for i in range(len(self.blocks)):
            b = self.blocks[i]
            if offset >= b.offset and offset - b.offset < b.get_size():
                return i, b
        return len(self.blocks) - 1, self.blocks[-1]

    def get_known_end_offset (self):
        return self.blocks[len(self.blocks) - 1].offset

    def get_part (self, offset, size):
        '''
        returns information from cache about data starting with given offset.
        The information returned may describe a smaller portion than the requested size
        but never more. The caller must call again to get information about the
        remaining data
        '''
        if size < 0:
            raise ValueError('negative size: {}'.format(size))
        if offset < 0:
            return hole_block(offset, min(size, -offset))
        bx, b = self.locate_block(offset)
        dmsg('offset 0x{:X} -> bx={} b={!r}', offset, bx, b)
        if b.kind == SCK_UNCACHED:
            assert b.offset <= offset and offset - b.offset < b.size
            return uncached_data_block(offset, min(size, b.offset + b.size - offset))
        elif b.kind == SCK_CACHED:
            b_size = b.get_size()
            assert b.offset <= offset and offset - b.offset < b_size
            n = min(size, b.offset + b_size - offset)
            o = offset - b.offset
            return cached_data_block(offset, b.data[o : o + n])
        elif b.kind == SCK_HOLE:
            assert b.offset <= offset
            assert b.size == 0 or offset - b.offset < b.size, repr((self, b, offset))
            if b.size == 0:
                return hole_block(offset, 0)
            else:
                return hole_block(offset, min(size, b.offset + b.size - offset))
        else:
            return b

    def _seek (self, offset):
        if self.seekable:
            assert offset >= 0, 'cannot seek to negative offsets'
            self.stream.seek(offset, SEEK_SET)
        else:
            if offset != self.pos:
                raise RuntimeError("unseekable cannot change pos from {} to {}".format(self.pos, offset))

    def _load (self, o, e):
        self._seek(o)
        while o < e:
            data = self.stream.read(e - o)
            dmsg('got 0x{} bytes', len(data) if data else 0)
            if not data:
                self._update_no_data(o)
                break
            self._update_data(o, data)
            o += len(data)

    def load (self, offset, size):
        o = zlx.int.pow2_round_down(offset, self.align)
        e = zlx.int.pow2_round_up(offset + size, self.align)
        self._load(o, e)
        dmsg('load o={:X} e={:X} => {!r}', o, e, self)

    def _merge_left (self, bx):
        if bx == 0 or bx >= len(self.blocks): return
        l = self.blocks[bx - 1]
        r = self.blocks[bx]
        if l.kind != r.kind: return
        if l.offset + l.get_size() == r.offset:
            if l.kind == SCK_CACHED:
                l.data[len(l.data):] = r.data
            elif l.kind == SCK_UNCACHED:
                l.size += r.size
            elif l.kind == SCK_HOLE:
                l.size += r.size
                if r.size == 0: l.size = 0 # hole before eof becomes eof
            del self.blocks[bx]

    def _merge_around (self, bx, count = 1):
        self._merge_left(bx)
        self._merge_left(bx + count)

    def _update_data (self, offset, data):
        dmsg('updating o=0x{:X} len=0x{:X}', offset, len(data))
        while data:
            bx, b = self.locate_block(offset)
            dmsg('ofs=0x{:X} len=0x{:X}. got block: {}', offset, len(data), b.desc())
            if b.kind == SCK_HOLE:
                if offset > b.offset:
                    self.blocks.insert(bx, uncached_data_block(b.offset, offset - b.offset) )
                    bx += 1
                self.blocks.insert(bx, cached_data_block(offset, bytearray(data)))
                self._merge_left(bx)
                b.offset = offset + len(data)
                return
            elif b.kind == SCK_UNCACHED:
                new_blocks = []
                b_end = b.offset + b.size
                if b.offset < offset:
                    new_blocks.append(uncached_data_block(b.offset, offset - b.offset))
                nb_len = min(b_end - offset, len(data))
                new_blocks.append(cached_data_block(offset, bytearray(data[0: nb_len])))
                data_end = offset + len(data)
                if data_end < b_end:
                    new_blocks.append(uncached_data_block(data_end, b_end - data_end))
                self.blocks[bx : bx + 1] = new_blocks
                self._merge_around(bx, len(new_blocks))
                offset += nb_len
                data = data[nb_len:]
            elif b.kind == SCK_CACHED:
                b_end = b.offset + len(b.data)
                update_len = min(b_end - offset, len(data))
                b.data[offset - b.offset : offset - b.offset + update_len] = data[0 : update_len]
                offset += update_len
                data = data[update_len:]
            else:
                raise sfmt("huh? {!r}", b)

    def _split_block (self, bx, offset):
        '''
        splits a block that has size (cached, uncached, hole) and returns the index and
        the block that starts with the given offset.
        '''
        blk = self.blocks[bx]
        assert blk.kind in (SCK_CACHED, SCK_UNCACHED, SCK_HOLE)
        assert blk.offset <= offset
        assert blk.offset + blk.get_size() > offset
        if blk.offset == offset: return bx, blk
        if blk.kind == SCK_CACHED:
            nblk = cached_data_block(offset, data = bytearray(blk.data[offset - blk.offset:]))
            blk.data[offset - blk.offset:] = b''
        else:
            nblk = blk.__class__(offset = offset, size = blk.offset + blk.size - offset)
        self.blocks.insert(bx + 1, nblk)
        return bx + 1, nblk

    def _discard_contiguous_data_blocks (self, bx):
        '''
        deletes all blocks from given index as long as they refer to data
        (cached/uncached) and updates the next non-data block (fix offset/size).
        '''
        offset = self.blocks[bx].offset
        while self.blocks[bx].kind in (SCK_CACHED, SCK_UNCACHED):
            del self.blocks[bx]
        assert self.blocks[bx].kind in (SCK_HOLE, )
        if self.blocks[bx].kind == SCK_HOLE:
            self.blocks[bx].size += offset - self.blocks[bx].offset
        self.blocks[bx].offset = offset
        self._merge_left(bx)

    def _update_no_data (self, offset):
        bx, blk = self.locate_block(offset)
        dmsg('no data at 0x{:X} => got block {!r}', offset, blk)
        if blk.kind in (SCK_CACHED, SCK_UNCACHED):
            bx, blk = self._split_block(bx, offset)
            self._discard_contiguous_data_blocks(bx)
        pass

stream_cache_load_request = namedtuple('stream_cache_load_request', 'offset size'.split())

#/* stream_cache_server ******************************************************/
class stream_cache_server (object):

    def __init__ (self, init_worker_count = 4, max_worker_count = 16):
        object.__init__(self)
        self.free_worker_count = 0
        self.max_worker_count = max_worker_count
        self.stream_queue = []
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.up = True
        dmsg('stream_cache_server initing {} workers...', init_worker_count)
        self.workers = [threading.Thread(target = self.worker) for i in range(init_worker_count)]
        for worker in self.workers:
            worker.start()

    def add_worker_ (self):
        th = threading.Thread(target = self.worker)
        self.workers.append(th)
        th.start()

    def wrap (self, stream, delay = 0):
        '''
        Returns a proxy stream that responds to get() by sending to a worked thread
        the request to load the missing parts from the cache and returns immediately
        the current cache
        '''
        if not isinstance(stream, stream_cache):
            stream = stream_cache(stream)
        return stream_cache_proxy(stream, self, delay = delay)

    def queue_stream_ (self, scp):
        '''
        adds to the queue a stream_cache_proxy
        '''
        with self.lock:
            if scp.queued:
                dmsg('stream already queued')
                return
            dmsg('stream queued')
            self.stream_queue.append(scp)
            if self.free_worker_count == 0 and len(self.workers) < self.max_worker_count:
                self.add_worker_()
            scp.queued = True
            self.cond.notify()

    def worker (self):
        dmsg('worker')
        while True:
            scp = None
            with self.lock:
                self.free_worker_count += 1
                while not self.stream_queue and self.up:
                    self.cond.wait()
                if not self.up:
                    dmsg('exiting worker...')
                    return
                scp = self.stream_queue.pop(0)
                self.free_worker_count -= 1
            while scp:
                scp.work_()
                with self.lock:
                    if not scp.load_queue:
                        scp.queued = False
                        scp = None

    def shutdown (self):
        with self.lock:
            self.up = False
            self.cond.notify_all()
        for worker in self.workers:
            worker.join()

#/* stream_cache_proxy *******************************************************/
class stream_cache_proxy (stream_cache):

    def __init__ (self, source, server, delay = 0):
        object.__init__(self)
        self.source = source
        self.server = server
        self.queued = False
        self.lock = threading.Lock()
        self.load_queue = []
        self.delay = delay
        self.updated = False

    def get_part (self, offset, size):
        b = self.source.get_part(offset, size)
        if b.kind == SCK_UNCACHED: self.queue_load_(offset, b.get_size())
        return b

    def get_known_end_offset (self):
        return self.source.get_known_end_offset()

    def queue_load_ (self, offset, size):
        if size == 0: return
        o = zlx.int.pow2_round_down(offset, self.source.align)
        e = zlx.int.pow2_round_up(offset + size, self.source.align)
        with self.lock:
            self.updated = False
            req = stream_cache_load_request(o, e - o)
            if req in self.load_queue:
                dmsg('load request: {!r} already queued', req)
            else:
                dmsg('append load request: {!r}', req)
                self.load_queue.append(req)
                self.server.queue_stream_(self)

    def reset_updated (self):
        with self.lock:
            u = self.updated
            self.updated = False
        return u

    def work_ (self):
        dmsg('start work')
        if self.delay: time.sleep(self.delay)
        while True:
            size = 0
            with self.lock:
                if not self.load_queue or not self.server.up: return
                offset, size = self.load_queue.pop(0)
            if size:
                dmsg('loading o={:X} s={:X}', offset, size)
                self.source.load(offset, size)
                self.updated = True

