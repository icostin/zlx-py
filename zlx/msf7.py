import zlx.int
import zlx.wire

MAGIC = b'Microsoft C/C++ MSF 7.00\r\n\x1A\x44\x53\0\0\0'

class error (RuntimeError): pass

superblock_codec = zlx.wire.stream_record_codec('msf_superblock',
        zlx.wire.stream_record_field('magic', zlx.wire.magic_codec(MAGIC)),
        zlx.wire.stream_record_field('block_size', zlx.wire.u32le),
        zlx.wire.stream_record_field('free_block_map_block', zlx.wire.u32le),
        zlx.wire.stream_record_field('block_count', zlx.wire.u32le),
        zlx.wire.stream_record_field('dir_size', zlx.wire.u32le),
        zlx.wire.stream_record_field('suttin', zlx.wire.u32le),
        zlx.wire.stream_record_field('dir_block_map_block', zlx.wire.u32le))

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

    def size_to_blocks (self, size):
        '''
        returns the number of blocks needed for a given size
        '''
        return (size + self.superblock.block_size - 1) // self.superblock.block_size

    def load_dir (self):
        if self.dir_blocks is None:
            self.dir_blocks = zlx.wire.stream_decode_array(self.stream,
                    zlx.wire.u32le,
                    self.size_to_blocks(self.superblock.dir_size))
            pass

# reader

