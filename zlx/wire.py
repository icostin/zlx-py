from __future__ import absolute_import
import struct
import io

import zlx.int
import zlx.record
import zlx.io

SEEK_SET = 0
SEEK_CUR = 1
SEEK_END = 2

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

CODEC_REGISTRY = {}

def default_desc (x):
    if isinstance(x, zlx.int.INT_TYPES):
        return '{}(0x{:X})'.format(x, x)
    return repr(x)

def register_codec (codec):
    if codec.name not in CODEC_REGISTRY:
        CODEC_REGISTRY[codec.name] = codec


class stream_codec (object):

    __slots__ = 'decode encode name desc'.split()

    def __init__ (self, name, decode, encode, desc = default_desc, register = True):
        self.name = name
        self.decode = decode
        self.encode = encode
        self.desc = desc
        if register: register_codec(self)

    def encode_to_bytes (self, value):
        f = io.BytesIO()
        self.encode(f, value)
        return f.getvalue()

    def decode_from_bytes (self, data):
        f = encoded_stream(data, self)
        return f.read()


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

def dec_hex_int_desc (value):
    return '{0}(0x{0:X})'.format(value)

INT_CODECS = []
for codec_name in PACK_FMT_DICT:
    codec = stream_codec(
            name = codec_name,
            decode = lambda stream, pack_fmt=PACK_FMT_DICT[codec_name], pack_len=len(struct.pack(PACK_FMT_DICT[codec_name], 0)): stream_decode_unpack(stream, pack_fmt, pack_len),
            encode = lambda stream, value, pack_fmt=PACK_FMT_DICT[codec_name]: stream_encode_pack(stream, value, pack_fmt),
            desc = dec_hex_int_desc)
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
    if name.startswith('!'):
        name = name[1:]
        register = False
    else:
        register = True
    return stream_codec(
            name = name,
            decode = lambda stream, _map = magic_list: stream_decode_byte_seq_map(stream, _map),
            encode = stream_encode_copy,
            register = register)

stream_record_field = zlx.record.make('record_field', 'name codec desc')

#* stream_record_codec ******************************************************/
class stream_record_codec (object):
    __slots__ = 'name fields record_type'.split()
    def __init__ (self, name_or_spec, *fields, **kw):
        if '\n' in name_or_spec:
            name = None
            fl = []
            for line in name_or_spec.splitlines():
                if '#' in line: line = line[0:line.index('#')]
                line = line.strip()
                if not line: continue
                if name is None:
                    if not line.endswith(':'):
                        raise RuntimeError('bad record spec - expecting "name:\n"')
                    name = line[0:-1].strip()
                else:
                    if ':' in line:
                        fn, fc = (x.strip() for x in line.split(':', 1))
                    else:
                        fc, fn = line.split()
                    codec = kw[fc] if fc in kw else CODEC_REGISTRY[fc]
                    field = stream_record_field(fn, codec, codec.desc)
                    fl.append(field)
            fl.extend(fields)
            fields = fl
        else:
            name = name_or_spec

        self.name = name
        fields = tuple(fields)
        self.fields = fields
        #print(repr(tuple((f.name for f in fields))))
        self.record_type = zlx.record.make(name,
            fields = tuple(f.name for f in fields),
            field_repr = { f.name: f.desc or default_desc for f in fields })
        register_codec(self)

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

    def read (self, count = None):
        if count is not None:
            return [self.decode(self.stream) for i in range(count)]
        return self.decode(self.stream)

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

    def __len__ (self):
        pos = self.stream.seek(0, SEEK_CUR)
        end = self.stream.seek(0, SEEK_END)
        self.stream.seek(pos, SEEK_SET)
        return end


#* stream *******************************************************************/
class stream (object):

    #__slots__ = 'stream codec_streams'.split()
    def __init__ (self, stream, *codec_list, **codec_map):
        if isinstance(stream, (bytes, bytearray)):
            stream = zlx.io.ba_view(stream)
        self.stream = stream
        if not codec_list and not codec_map:
            codec_map = CODEC_REGISTRY
        for codec in codec_list:
            if isinstance(codec, (str,)):
                codec = CODEC_REGISTRY[codec]
            self.add_codec(codec)
        for name, codec in codec_map.items():
            self.add_codec(codec, name)

    def add_codec (self, codec, name = None):
        if name is None: name = codec.name
        setattr(self, name, encoded_stream(self.stream, codec))

    def __len__ (self):
        pos = self.stream.seek(0, SEEK_CUR)
        end = self.stream.seek(0, SEEK_END)
        self.stream.seek(pos, SEEK_SET)
        return end

    def __getitem__ (self, index):
        if isinstance(index, tuple):
            offset, count = index
            self.stream.seek(offset)
            return self.stream.read(count)
        else:
            self.stream.seek(index)
            return self.stream.read(1)[0]

    def seekable (self):
        return self.stream.seekable()

    def seek (self, offset, whence = SEEK_SET):
        return self.stream.seek(offset, whence)

    def read (self, size = -1):
        return self.stream.read(size)

