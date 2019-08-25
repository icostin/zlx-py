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
    __slots__ = 'decode encode name'.split()
    def __init__ (self, name, decode, encode):
        self.name = name
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

def stream_decode_array (stream, codec, count):
    return tuple(codec.decode(stream) for i in range(count))

INT_CODECS = []
for codec_name in PACK_FMT_DICT:
    codec = stream_codec(
            name = codec_name,
            decode = lambda stream, pack_fmt=PACK_FMT_DICT[codec_name], pack_len=len(struct.pack(PACK_FMT_DICT[codec_name], 0)): stream_decode_unpack(stream, pack_fmt, pack_len),
            encode = lambda stream, value, pack_fmt=PACK_FMT_DICT[codec_name]: stream_encode_pack(stream, value, pack_fmt))
    globals()[codec_name] = codec
    INT_CODECS.append(codec)

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

def magic_codec (name, *magic_list):
    return stream_codec(
            name = name,
            decode = lambda stream, _map = magic_list: stream_decode_byte_seq_map(stream, _map),
            encode = stream_encode_copy)

def default_desc (x):
    if isinstance(x, zlx.int.INT_TYPES):
        return '{}(0x{:X})'.format(x, x)
    return repr(x)

stream_record_field = zlx.record.make('record_field', 'name codec desc')

#* stream_record_codec ******************************************************/
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


#* encoded_stream ***********************************************************/
class encoded_stream (object):

    __slots = 'stream decode encode'.split()
    def __init__ (self, stream, codec):
        self.stream = stream
        self.decode = codec.decode
        self.encode = codec.encode

    def read (self):
        return self.decode(stream)

    def write (self, value):
        self.encode(self.stream, value)

    def __getitem__ (self, index):
        if isinstance(index, tuple):
            offset, count = index
            self.stream.seek(offset)
            return tuple(self.decode(stream) for i in range(count))
        else:
            self.stream.seek(index)
            return self.decode(self.stream)

    def __setitem__ (self, offset, value):
        self.stream.seek(offset)
        self.encode(self.stream, value)


#* stream *******************************************************************/
class stream (object):

    #__slots__ = 'stream codec_streams'.split()
    def __init__ (self, stream, *codec_list, **codec_map):
        if isinstance(stream, (bytes, bytearray)):
            stream = zlx.io.ba_view(stream)
        self.stream = stream
        for codec in codec_list:
            print('add codec {}'.format(codec.name))
            setattr(self, codec.name, encoded_stream(stream, codec))
        for name, codec in codec_map.items():
            setattr(self, name, encoded_stream(stream, codec))

