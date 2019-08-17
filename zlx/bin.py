import struct

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
        if offset < 0 or offset > self.length - self.__class__.PACK_LEN: raise IndexError(offset)
        return struct.unpack_from(self.__class__.PACK_FMT, self.data, self.disp + offset)[0]

    def __setitem__ (self, offset, value):
        if offset < 0 or offset > self.length - self.__class__.PACK_LEN: raise IndexError(offset)
        struct.pack_into(self.__class__.PACK_FMT, self.data, self.disp + offset, value)
        return value

    pass # bin_pack_acc

for a in PACK_ACC_LIST:
    n = 'bin_acc_' + a
    globals()[n] = type(n, (bin_pack_acc,), dict(PACK_FMT=PACK_FMT_DICT[a], PACK_LEN=PACK_LEN_DICT[a]))

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

    @property
    def b (self): 
        return bin_acc_u8(self.data, self.disp, self.length)

    @property
    def u8 (self): 
        return bin_acc_u8(self.data, self.disp, self.length)

    @property
    def i8 (self): 
        return bin_acc_i8(self.data, self.disp, self.length)

    @property
    def u16le (self): 
        return bin_acc_u16le(self.data, self.disp, self.length)

    @property
    def u16be (self): 
        return bin_acc_u16be(self.data, self.disp, self.length)

    @property
    def i16le (self): 
        return bin_acc_i16le(self.data, self.disp, self.length)

    @property
    def i16be (self): 
        return bin_acc_i16be(self.data, self.disp, self.length)

    @property
    def u32le (self): 
        return bin_acc_u32le(self.data, self.disp, self.length)

    @property
    def u32be (self): 
        return bin_acc_u32be(self.data, self.disp, self.length)

    @property
    def i32le (self): 
        return bin_acc_i32le(self.data, self.disp, self.length)

    @property
    def i32be (self): 
        return bin_acc_i32be(self.data, self.disp, self.length)

    @property
    def u64le (self): 
        return bin_acc_u64le(self.data, self.disp, self.length)

    @property
    def u64be (self): 
        return bin_acc_u64be(self.data, self.disp, self.length)

    @property
    def i64le (self): 
        return bin_acc_i64le(self.data, self.disp, self.length)

    @property
    def i64be (self): 
        return bin_acc_i64be(self.data, self.disp, self.length)


