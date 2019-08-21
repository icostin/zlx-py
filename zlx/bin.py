import struct
import sys
import zlx.int

if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from StringIO import StringIO

PACK_ACC_LIST = 'u8 i8 u16le u16be i16le i16be u32le u32be i32le i32be u64le u64be i64le i64be'.split()

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

PACK_LEN_DICT = {
    'u8': 1,
    'i8': 1,
    'u16le': 2,
    'u16be': 2,
    'i16le': 2,
    'i16be': 2,
    'u32le': 4,
    'u32be': 4,
    'i32le': 4,
    'i32be': 4,
    'u64le': 8,
    'u64be': 8,
    'i64le': 8,
    'i64be': 8,
}

class bin_pack_acc (object):

    __slots__ = 'data disp length'.split()

    def __init__ (self, data, disp, length):
        self.data = data
        self.disp = disp
        self.length = length
        return

    def __getitem__ (self, offset = 0):
        if isinstance(offset, tuple) and len(offset) == 2:
            offset, count = offset
            return tuple(self[offset + i * self.__class__.PACK_LEN] for i in range(count))
        if offset < 0 or offset > self.length - self.__class__.PACK_LEN: raise IndexError(offset)
        return struct.unpack_from(self.__class__.PACK_FMT, self.data, self.disp + offset)[0]

    def __setitem__ (self, offset, value):
        if offset < 0 or offset > self.length - self.__class__.PACK_LEN: raise IndexError(offset)
        struct.pack_into(self.__class__.PACK_FMT, self.data, self.disp + offset, value)
        return value

    pass # bin_pack_acc

class accessor (object):

    __slots__ = 'data disp length'.split()
    def __init__ (self, data, disp = 0, length = None, dup = False):
        if dup: data = bytearray(data)
        self.data = data
        self.disp = disp
        self.length = len(data) - disp if length is None else length
        return

    def __getitem__ (self, index):
        if isinstance(index, tuple):
            offset, length = index
            return bytes(self.data[self.disp + offset : self.disp + offset + length])
        else:
            return self.u8[index]

for a in PACK_ACC_LIST:
    n = 'bin_acc_' + a
    pa = type(n, (bin_pack_acc,), dict(PACK_FMT=PACK_FMT_DICT[a], PACK_LEN=PACK_LEN_DICT[a]))
    globals()[n] = pa
    setattr(accessor, a, property(lambda self, pa=pa: pa(self.data, self.disp, self.length)))

def unpack_from_stream (stream, offset, pack_fmt, pack_len):
    stream.seek(offset)
    return struct.unpack(pack_fmt, stream.read(pack_len))[0]

def pack_to_stream (stream, offset, pack_fmt, value):
    stream.seek(offset)
    stream.write(struct.pack(pack_fmt, value))
    return

class io_pack_accessor (object):

    __slots__ = 'stream disp length'.split()

    def __init__ (self, stream, disp = 0, length = None):
        self.stream = stream
        self.disp = disp
        self.length = length
        return

    def check_range (self, offset, size):
        return offset >= 0 and (self.length is None or offset + size <= self.length)

    def __getitem__ (self, index):
        if isinstance(index, tuple):
            offset, count = index
            return tuple(self[offset + i * self.PACK_LEN] for i in range(count))
        else:
            offset = index

        if not self.check_range(offset, self.PACK_LEN):
            raise IndexError('out of range')
        return unpack_from_stream(self.stream, offset,
                self.PACK_FMT, self.PACK_LEN)

    def __setitem__ (self, offset, value):
        if not self.check_range(offset, self.PACK_LEN):
            raise IndexError('out of range')
        return pack_to_stream(self.stream, offset, self.PACK_FMT, value)

class io_accessor (object):

    __slots__ = 'stream disp length'.split()

    def __init__ (self, stream, disp = 0, length = None):
        self.stream = stream
        self.disp = disp
        self.length = length
        return

    def check_range (self, offset, size):
        return offset >= 0 and (self.length is None or offset + size <= self.length)
    def __getitem__ (self, index):
        if isinstance(index, tuple):
            offset, length = index
            if not self.check_range(offset, length):
                raise IndexError('out of range')
            self.stream.seek(self.disp + offset)
            return bytes(self.stream.read(length))
        else:
            return self.u8[index]
# class io_accessor


for a in PACK_ACC_LIST:
    n = 'io_accessor_' + a
    pa = type(n, (io_pack_accessor,),
            dict(PACK_FMT=PACK_FMT_DICT[a], PACK_LEN=PACK_LEN_DICT[a]))
    globals()[n] = pa
    setattr(io_accessor, a, property(lambda self, pa=pa: pa(self.stream, self.disp, self.length)))

NO_OFFSET = -1
PLAIN_OFFSET = 128
GROUP_4_OFFSET = 4

NO_HEX = None

NO_CHARS = None
PRINTABLE_ASCII_CHARS_MAP = tuple('.' if n < 0x20 or n >= 0x7F else chr(n) for n in range(256))

OFFSET_8HEX = lambda n: '{:08X}: '.format(n)
OFFSET_HIDE = lambda n: ''

def byte_as_printable_ascii_char_printer (data, offset):
    return (PRINTABLE_ASCII_CHARS_MAP[data[offset]], 1)

def hex_char_dump (
        data,
        data_offset = 0,
        data_length = None,
        display_data_offset = None,
        display_row_offset = None,
        display_row_count = None,
        offset_printer = None,
        char_printer = byte_as_printable_ascii_char_printer,
        width = 0x10,
        line_prefix = '',
        line_suffix = '\n',
        offset_suffix = ': ',
        mod_sep = { 1: ' ', 4: '  ' },
        hex_char_sep = '    ',
        no_data_pad = '..',
        no_char_pad = ' ',
        ):

    if isinstance(data, (bytes, bytearray)):
        data = zlx.bin.accessor(data).u8

    if data_length is None:
        data_length = len(data) - data_offset

    if display_data_offset is None:
        display_data_offset = data_offset
    if display_row_offset is None:
        display_data_offset = display_data_offset - display_data_offset % width
    if display_row_count is None:
        items_in_first_row = width - (display_data_offset - display_row_offset)
        display_row_count = 1
        if data_length > items_in_first_row:
            display_row_count += (data_length - items_in_first_row + width - 1) // width

    if offset_printer is None:
        last_offset = display_data_offset + (display_row_count - 1) * width
        offset_digits = (zlx.int.log2_ceil(last_offset) + 3) // 4

        offset_printer = lambda x, fmt='{{:0{}X}}: '.format(offset_digits): fmt.format(x)

    offset_delta = data_offset - display_data_offset
    o = StringIO()
    for r in range(display_row_count):
        o.write(offset_printer(display_row_offset + r * width))
        for c in range(width):
            offset = display_row_offset + r * width + c + offset_delta
            if c > 0:
                for b in sorted(mod_sep.keys(), reverse=True):
                    if c % b == 0:
                        o.write(mod_sep[b])
                        break
            if offset < data_offset or offset >= data_offset + data_length:
                o.write(no_data_pad)
            else:
                o.write('{:02X}'.format(data[offset]))
        o.write(hex_char_sep)
        inc = 1
        for c in range(width):
            inc -= 1
            if inc > 0: next
            offset = display_row_offset + r * width + c + offset_delta
            if offset < data_offset or offset >= data_offset + data_length:
                o.write(no_char_pad)
            else:
                s, inc = char_printer(data, offset)
                o.write(s)
        o.write('\n')

    return o.getvalue()

