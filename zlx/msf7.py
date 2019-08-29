import zlx.int
import zlx.io
import zlx.wire
import zlx.bin

MAGIC = b'Microsoft C/C++ MSF 7.00\r\n\x1A\x44\x53\0\0\0'

class error (RuntimeError): pass

superblock_codec = zlx.wire.stream_record_codec('''
msf_superblock:
msf7_magic  magic
u32le       block_size
u32le       free_block_map_block
u32le       block_count
u32le       dir_size
u32le       suttin
u32le       dir_block_map_block
''', msf7_magic=zlx.wire.magic_codec('msf7_magic', MAGIC))

class reader (object):
    '''
    Provides read-only access to an MSF7 container file
    build it with:
        reader(file_path)   OR
        reader(stream)
    '''

    def __init__ (self, source):
        if isinstance(source, str):
            self.stream = open(source, 'rb')
        else:
            self.stream = source
        self.superblock = superblock_codec.decode(self.stream)
        if self.superblock.block_size not in (0x200, 0x400, 0x800, 0x1000):
            raise error('invalid block size {}'.format(
                self.superblock.block_size))
        if self.superblock.free_block_map_block not in (1, 2):
            raise error('invalid free block map block {}'.format(
                self.superblock.free_block_map_block))
        self.dir_blocks = None

    def size_to_blocks (self, size):
        '''
        returns the number of blocks needed for a given size
        '''
        return (size + self.superblock.block_size - 1) // self.superblock.block_size

    def load_dir (self):
        if self.dir_blocks is None:
            self.stream.seek(self.superblock.dir_block_map_block * self.superblock.block_size)
            self.dir_blocks = zlx.wire.stream_decode_array(self.stream,
                    zlx.wire.u32le,
                    self.size_to_blocks(self.superblock.dir_size))
            self.dir_stream = zlx.wire.stream(
                zlx.io.chunked_stream((
                    zlx.io.chunk(
                        self.stream,
                        block * self.superblock.block_size,
                        self.superblock.block_size) \
                    for block in self.dir_blocks)))
            self.stream_count = self.dir_stream.u32le.read()
            self.stream_size_table = self.dir_stream.u32le.read(self.stream_count)
            self.streams = []
            for stream_size in self.stream_size_table:
                s = zlx.wire.stream(
                        zlx.io.chunked_stream((
                        zlx.io.chunk(self.stream,
                            block * self.superblock.block_size,
                            self.superblock.block_size) \
                        for block in self.dir_stream.u32le.read(self.size_to_blocks(stream_size)))))
                self.streams.append(s)
            #self.dir_stream.seek(0)
            #dir_data = self.dir_stream.read()
            #print('stream dir:\n{}'.format(zlx.bin.hex_char_dump(dir_data)))

# reader

