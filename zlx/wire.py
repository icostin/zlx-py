import struct
import zlx.int
import zlx.record

class decode_error (RuntimeError): pass

PACK_FMT_DICT = {
    'u8': 'B',
    'i8': 'b',
    'u16le': '<H',
    'u16be': '>H',
    'i16le': '<h',
    'i16be': '>h',
    'u32le': '<I',
    'u32be': '>I',
    'i32le': '<i',
    'i32be': '>i',
    'u64le': '<Q',
    'u64be': '>Q',
    'i64le': '<q',
    'i64be': '>q',
}

class stream_codec (object):
    __slots__ = 'decode encode'.split()
    def __init__ (self, decode, encode):
        self.decode = decode
        self.encode = encode

def stream_decode_unpack (stream, pack_fmt, pack_len):
    data = stream.read(pack_len)
    try:
        return struct.unpack(pack_fmt, data)[0]
    except struct.error:
        raise decode_error('truncated data')

def stream_encode_pack (stream, value, pack_fmt):
    stream.write(struct.pack(pack_fmt, value))

def stream_decode_copy (stream, size, throw_on_no_match = True):
    v = stream.read(size)
    if len(v) != size and throw_on_no_match:
        raise decode_error('truncated data')
    return v

def stream_encode_copy (stream, value):
    stream.write(value)

for codec in PACK_FMT_DICT:
    globals()[codec] = stream_codec(
            decode = lambda stream, pack_fmt=PACK_FMT_DICT[codec], pack_len=len(struct.pack(PACK_FMT_DICT[codec], 0)): stream_decode_unpack(stream, pack_fmt, pack_len),
            encode = lambda stream, value, pack_fmt=PACK_FMT_DICT[codec]: stream_encode_pack(stream, value, pack_fmt))

def stream_decode_byte_seq_map (stream, byte_seq_map, throw_on_no_match = True):
    max_len = max(len(k) for k in byte_seq_map)
    data = stream.read(max_len)
    match = None
    for k in byte_seq_map:
        if data[0:len(k)] == k:
            if match is None or len(k) > len(match):
                match = k
    if match is None:
        if throw_on_no_match: raise decode_error('no match')
        match_len = 0
    else:
        match_len = len(match)
        if isinstance(byte_seq_map, dict):
            match = byte_seq_map[match]
    stream.seek(match_len - max_len, 1)
    return match

def magic_codec (*magic_list):
    return stream_codec(
            decode = lambda stream, _map = magic_list: stream_decode_byte_seq_map(stream, _map),
            encode = stream_encode_copy)

def default_desc (x):
    if isinstance(x, zlx.int.INT_TYPES):
        return '{}(0x{:X})'.format(x, x)
    return repr(x)

stream_record_field = zlx.record.make('record_field', 'name codec desc')

class stream_record_codec (object):
    __slots__ = 'fields record_type'.split()
    def __init__ (self, name, *fields):
        self.fields = fields
        print(repr(tuple((f.name for f in fields))))
        self.record_type = zlx.record.make(name,
            fields = tuple(f.name for f in fields),
            field_repr = { f.name: f.desc or default_desc for f in fields })

    def decode (self, stream):
        return self.record_type(**{f.name: f.codec.decode(stream) for f in self.fields})

    def encode (self, stream, value):
        for f in self.fields:
            f.codec.encode(stream, getattr(value, f.name))

