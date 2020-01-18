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

#/* stream_cache *************************************************************/
class stream_cache (object):

    def __init__ (self, stream, align = 4096, assume_size = None):

        object.__init__(self)
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

################################################################################
################################################################################
################################################################################

class negative_offset_error (RuntimeError): pass
class malformed_range_error (RuntimeError): pass
class offset_outside_block_error (RuntimeError): pass

#* cached_block *************************************************************
class cached_block:
    '''
    Base class for various cached blocks.
    '''

    is_uncached_block = False
    is_data_block = False
    is_hole_block = False
    is_end_block = False

# cached_block.__init()
    def __init__ (self, time, offset):
        self.time = time
        self.offset = offset

# cached_block.contains_offset()
    def contains_offset (self, offset):
        return offset >= self.offset and offset - self.offset < self.size

# cached_block.end_offset
    @property
    def end_offset (self):
        return self.offset + self.size

# cached_block._split()
    def _split (self, offset):
        if not self.contains_offset(offset):
            raise offset_outside_block_error(offset, block)

        if offset == self.offset:
            return [ self ]

        return self._split_block(offset = offset)

# cached_block._split_block()
    def _split_block (self, offset):
        raise NonImplementedError()

# cached_block.__eq__()
    def __eq__ (self, other):
        if self.__class__ is not other.__class__:
            return False
        for field in self.__slots__:
            if getattr(self, field) != getattr(other, field):
                return False
        return True

# cached_block - end class

#* cached_data_block ********************************************************
class cached_data_block (cached_block):
    '''
    Cached data block
    '''
    __slots__ = 'time offset data'.split()
    is_data_block = True

# cached_data_block.__init__()
    def __init__ (self, time, offset, data):
        cached_block.__init__(self, time, offset)
        self.data = data

# cached_data_block.size
    @property
    def size (self):
        return len(self.data)

# cached_data_block.data_snippet()
    def data_snippet (self):
        if len(self.data) > 12:
            return '{!r}...{!r}'.format(self.data[0:8], self.data[-4:])
        else: return '{!r}'.format(self.data)

# cached_data_block.__repr__()
    def __repr__ (self):
        return '{}(offset=0x{:X}, size=0x{:X}, time={}, data={})'.format(
                self.__class__.__name__,
                self.offset, len(self.data), self.time, self.data_snippet())

# cached_data_block._split_block()
    def _split_block (self, offset):
        data_offset = offset - self.offset
        return [
            self.__class__(
                time = self.time,
                offset = self.offset,
                data = self.data[0 : data_offset]),
            self.__class__(
                time = self.time,
                offset = offset,
                data = self.data[data_offset : ])]

# cached_data_block - end

#* cached_hole_block ********************************************************
class cached_hole_block (cached_block):
    __slots__ = 'time offset size'.split()
    is_hole_block = True

# cached_hole_block.__init__()
    def __init__ (self, time, offset, size):
        cached_block.__init__(self, time, offset)
        self.size_ = size

# cached_hole_block.__repr__()
    def __repr__ (self):
        return '{}(offset=0x{:X}, size={}, time={})'.format(
                self.__class__.__name__,
                self.offset, self.size, self.time)

# cached_hole_block._split_block()
    def _split_block (self, offset):
        return [
            self.__class__(
                time = self.time,
                offset = self.offset,
                size = offset - self.offset),
            self.__class__(
                time = self.time,
                offset = offset,
                size = self.end_offset - offset)]
        self.size = offset - self.offset
        return nb

#* cached_end_block *********************************************************
class cached_end_block (cached_block):
    __slots__ = 'time offset'.split()
    is_end_block = True

# cached_end_block.size
    @property
    def size (self):
        return 0

# cached_end_block.contains_offset()
    def contains_offset (self, offset):
        return offset >= self.offset

# cached_end_block.__repr__()
    def __repr__ (self):
        return '{}(offset=0x{:X}, time={})'.format(
                self.__class__.__name__,
                self.offset, self.time)

# cached_end_block._split_block()
    def _split_block (self, offset):
        return [
            uncached_block(
                offset = self.offset,
                size = offset - self.offset),
            self.__class__(
                time = self.time,
                offset = offset)]

# cached_end_block - end class

#* uncached_block ***********************************************************
class uncached_block (cached_block):

    __slots__ = 'offset size'.split()

    is_uncached_block = True

# uncached_block.__init__()
    def __init__ (self, offset, size):
        self.offset = offset
        self.size = size

# uncached_block.time
    @property
    def time (self):
        return HISTORY_BEGIN_TIME

# uncached_block.__repr__()
    def __repr__ (self):
        return '{}(offset=0x{:X}, size={})'.format(
                self.__class__.__name__,
                self.offset, self.size)

# uncached_block._split_block()
    def _split_block (self, offset):
        return [
            self.__class__(
                offset = self.offset,
                size = offset - self.offset),
            self.__class__(
                offset = offset,
                size = self.end_offset - offset)]

# uncached_block - end class

HISTORY_BEGIN_TIME = -sys.float_info.max

#* linear_data_cache ********************************************************/
class linear_data_cache:
    '''
    Caches data organized in a linear address space.
    Can be used for cache of files / data streams, memory layouts, etc.
    '''

# linear_data_cache.__init__()
    def __init__ (self, time_source):
        self.time_source_ = time_source
        self.blocks_ = [cached_end_block(HISTORY_BEGIN_TIME, 0)]

    @property
    def block_count (self):
        return len(self.blocks_)

# linear_data_cache.end_block
    @property
    def end_block (self):
        return self.blocks_[-1]

# linear_data_cache.end_block_index_()
    @property
    def end_block_index_ (self):
        return len(self.blocks_) - 1

# linear_data_cache.size
    @property
    def size (self):
        '''
        known cached size of data - includes holes
        '''
        return self.end_block.offset

# linear_data_cache.locate_block()
    def locate_block (self, offset):
        '''
        Retrieves the block with its position that contains the given offset.
        Raises error on negative offsets.
        Returns (None, end_block_index) for offset beyond end_block.
        '''
        if offset < 0: raise negative_offset_error(offset)
        for i in range(len(self.blocks_)):
            b = self.blocks_[i]
            if b.contains_offset(offset): return (b, i)
        raise RuntimeError("BUG: should have found a block")

# linear_data_cache._split_block()
    def _split_block (self, offset):
        '''
        Splits the block containing the offset and returns the index
        of the new block starting at the given offset.
        If offset is out of range, it returns None (this is true for
        the end block as well).
        If the given offset is the beginning of and existing block
        then the index of that block is returned
        '''
        b, i = self.locate_block(offset)
        sbl = b._split(offset = offset)
        self.blocks_[i : i + 1] = sbl
        return i + len(sbl) - 1

# linear_data_cache._add_block()
    def _add_block (self, blk):
        start_block_index = self._split_block(offset = blk.offset)
        end_block_index = self._split_block(offset = blk.end_offset)
        self.blocks_[start_block_index : end_block_index] = [ blk ]
        if self.blocks_[end_block_index].is_end_block:
            self.blocks_[end_block_index].time = blk.time

# linear_data_cache.add_data()
    def add_data (self, data, offset, time = None):
        if time is None: time = self.time_source_()
        self._add_block(cached_data_block(time, offset, data))

# linear_data_cache.del_range()
    def del_range (self, offset, size = None, end_offset = None):
        if size is not None:
            end_offset = offset + size
        if end_offset >= self.size:
            end_offset = self.size
        sx = self._split_block(offset)
        if sx > 0 and self.blocks_[sx - 1].is_uncached_block:
            sx -= 1
            offset = self.blocks_[sx].offset
        ex = self._split_block(end_offset)
        if self.blocks_[ex].is_uncached_block:
            end_offset = self.blocks_[ex].end_offset
            ex += 1
        self.blocks_[sx : ex] = [
                uncached_block(
                    offset = offset,
                    size = end_offset - offset) ]

# linear_data_cache.blocks()
    def blocks (self):
        '''
        Returns iterable that goes through all blocks from offset 0 to known EOF
        '''
        return self.blocks_

    def __repr__ (self):
        return 'linear-data-cache(nblk={}{})'.format(len(self.blocks_), ','.join(('\n  {!r}'.format(b) for b in self.blocks_)))

#* cached_stream_time_source ************************************************
try:
    time.monotonic()
    cached_stream_time_source = time.monotonic
except:
    cached_stream_time_source = time.time

#* linear_data_cache_test ***************************************************

def linear_data_cache_test ():

    def _ldc_test_time_source (time_seed):
        time_seed[0] += 1
        return time_seed[0]
    tsrc = lambda ts = [0]: _ldc_test_time_source(ts)
    assert tsrc() == 1
    assert tsrc() == 2

    def check (ldc, bl):
        if ldc.block_count != len(bl):
            raise RuntimeError('expecting {} blocks, not {}'.format(len(bl), ldc.block_count))
        for i in range(ldc.block_count):
            if not ldc.blocks_[i] == bl[i]:
                raise RuntimeError('expecting {!r} not {!r}'.format(bl[i], ldc.blocks_[i]))

    ldc = linear_data_cache(tsrc)
    dmsg('initial ldc: {!r}', ldc)
    assert ldc.end_block.offset == 0
    check(ldc, [cached_end_block(HISTORY_BEGIN_TIME, 0)])

    ldc.add_data(data = b'abcde', offset = 10)
    dmsg('add "abcde" at 10: {!r}', ldc)
    check(ldc, [
        uncached_block(0, 10),
        cached_data_block(time = 3, offset = 10, data = b'abcde'),
        cached_end_block(time = 3, offset = 15)])

    ldc.del_range(offset = 12, end_offset = 14)
    omsg('del [12,14): {!r}', ldc)
    check(ldc, [
        uncached_block(0, 10),
        cached_data_block(time = 3, offset = 10, data = b'ab'),
        uncached_block(12, 2),
        cached_data_block(time = 3, offset = 14, data = b'e'),
        cached_end_block(time = 3, offset = 15)])

    ldc.del_range(offset = 13, size = 1000)
    omsg('del [13, 1013): {!r}', ldc)
    check(ldc, [
        uncached_block(0, 10),
        cached_data_block(time = 3, offset = 10, data = b'ab'),
        uncached_block(12, 3),
        cached_end_block(time = 3, offset = 15)])

    omsg('linear_data_cache test passed')

#* rw_cached_stream *********************************************************
class rw_cached_stream (io.BufferedIOBase):
    def __init__ (self, raw, align = 4096,
            cached_data_max_size = 1024 * 1024):
        self.raw_ = raw
        self.lock_ = threading.Lock()
        self.cond_ = threading.Condition(self.lock_)
        try:
            if not raw_.seekable(): raise IOError()
            self.pos_ = raw_.seek(0, SEEK_CUR)
            self.seekable_ = True
        except IOError as e:
            self.seekable_ = False
        return
    def _write_dirty_buffers (self):
        return

    def flush (self):
        self._write_dirty_buffers()
        self.raw_.flush()

    def close (self):
        self._write_dirty_buffers()
        self.raw_.close()

    def seekable (self):
        return self.seekable_

    def tell (self):
        return self.pos_


