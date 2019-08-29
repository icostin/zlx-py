from __future__ import absolute_import
import sys
import io

def omsg (fmt, *l, **kw):
    return sys.stdout.write((fmt + '\n').format(*l, **kw))

def emsg (fmt, *l, **kw):
    return sys.stderr.write((fmt + '\n').format(*l, **kw))

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

    def seek (self, offset, whence=io.SEEK_SET):
        if whence == io.SEEK_SET: pass
        elif whence == io.SEEK_CUR: offset += self.pos
        elif whence == io.SEEK_END: offset += self.size
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
    def seek (self, offset, whence = io.SEEK_SET):
        if whence == io.SEEK_SET: pass
        elif whence == io.SEEK_CUR: offset += self.pos
        elif whence == io.SEEK_END: offset += len(self.ba)
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


