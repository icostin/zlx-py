import io
import sys

def hex_char_dump_test ():
    import zlx.bin

    d = zlx.bin.hex_char_dump(
            data = b'xxx\x01a\x02b\x03c\x04d\x05efghijklmnopqrstuvwxyz',
            data_offset = 3,
            data_length = 30,
            display_data_offset = 0x12307,
            display_row_offset = 0x12302,
            width = 13)
    print(d)
    assert d.strip() == '''
12302: .. .. .. ..  .. 01 61 02  62 03 63 04  64         .a.b.c.d
1230F: 05 65 66 67  68 69 6A 6B  6C 6D 6E 6F  70    .efghijklmnop
1231C: 71 72 73 74  75 76 77 78  79 .. .. ..  ..    qrstuvwxy
'''.strip()
    return

def wire_test ():
    import zlx.wire
    assert zlx.wire.u8.decode(io.BytesIO(b'abc')) == 0x61
    assert zlx.wire.u16le.decode(io.BytesIO(b'abc')) == 0x6261
    assert zlx.wire.u16be.decode(io.BytesIO(b'abc')) == 0x6162

    try:
        zlx.wire.u8.decode(io.BytesIO(b''))
    except zlx.wire.decode_error as e:
        assert 'truncated data' in e.args

    mm = {b'aragula': 0, b'barabu': 1, b'barz': 2, b'barabul': 3}
    assert zlx.wire.stream_decode_byte_seq_map(io.BytesIO(b'barabula'), mm) == 3

    assert zlx.wire.stream_decode_byte_seq_map(io.BytesIO(b'xbarabula'), mm, False) is None

    try:
        zlx.wire.stream_decode_byte_seq_map(io.BytesIO(b'xbarabula'), mm)
    except zlx.wire.decode_error as e:
        assert 'no match' in e.args[0]

    mc = zlx.wire.magic_codec('file_formats', b'MZ', b'\x7FELF', b'PNG')
    try:
        mc.decode(io.BytesIO(b'bla'))
    except zlx.wire.decode_error as e:
        assert 'no match' in e.args[0]

    f = io.BytesIO(b'MZAP')
    assert mc.decode(f) == b'MZ'
    assert f.read() == b'AP'

    field = zlx.wire.stream_record_field
    ABC = zlx.wire.stream_record_codec(
            '''
            ABC: # my ABC record
                magic: abc_magic # this is magic
                aaa: u16be
                u32le bbb
            ''',
            # field('magic', zlx.wire.magic_codec('abc', b'ABC\n', register = False)),
            # field('aaa', zlx.wire.u16be),
            # field('bbb', zlx.wire.u32le),
            field('ccc', zlx.wire.u8), abc_magic=zlx.wire.magic_codec('abc', b'ABC\n'))
    f = io.BytesIO(b'ABC\ndefghijk')
    o = ABC.decode(f)
    print('o = {!r}'.format(o))
    assert o.aaa == 0x6465
    assert o.bbb == 0x69686766
    assert o.ccc == 0x6A
    assert o.magic == b'ABC\n'

    s = zlx.wire.stream(b'0123456789', *zlx.wire.INT_CODECS)
    print('bla {}'.format(s.u32be[1]))
    assert s.u8[3] == 0x33
    return

def io_test ():
    import zlx.io
    b1 = io.BytesIO(b'0123456789abcdefghijklmnopqrstuvwxyz')
    b2 = io.BytesIO(b'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    cs = zlx.io.chunked_stream((zlx.io.chunk(b1, 1, 5), zlx.io.chunk(b2, 5, 5),
        zlx.io.chunk(b1, 3, 3)))
    r = cs.read(12)
    print(repr(r))
    assert r == b'12345FGHIJ34'

    ba = bytearray(b'012345')
    bav = zlx.io.ba_view(ba)
    assert len(bav) == 6
    bav.seek(-3, io.SEEK_END)
    assert bav.read(5) == b'345'
    return

def record_test ():
    import zlx.record
    import zlx.int
    P = zlx.record.make('Point', 'x y')
    p = P(1, 2)
    print(repr(p))

    # FBZ = zlx.record.make('FBZ', 'foo:u8 bar:u32le baz:u16be', field_repr=dict(a=zlx.int.hex, b=zlx.int.hex, c=zlx.int.hex))
    # f = zlx.bin.io_accessor(io.BytesIO(b'@abcdefghijk'))
    # fbz = FBZ.from_io_accessor(f, 1)[0]
    # print(repr(fbz))
    # assert fbz.foo == 0x61
    # assert fbz.bar == 0x65646362
    # assert fbz.baz == 0x6667
    return


def pe_test ():
    import zlx.bin
    import zlx.pe
    ba = zlx.wire.stream(b'MZ\0\0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\x80\0\0\0')
    x = zlx.pe.parse_mz_header(ba)
    print(repr(x))
    assert x.magic == zlx.pe.MZ_MAGIC
    assert x.e_lfanew == 0x80

def map_pe (input_path, output_path):
    import zlx.io
    import zlx.bin
    import zlx.pe
    ba = zlx.wire.stream(zlx.io.bin_load(input_path))
    mzh = zlx.pe.parse_mz_header(ba)
    peh = zlx.pe.parse_pe_header(ba, offset = mzh.e_lfanew)
    #print(repr(mzh))
    #print(repr(peh))
    image = zlx.pe.map_parsed_pe(ba, peh)
    assert image[0:2] == b'MZ', 'image should start with MZ'
    hw_rva = image.find(b'Hello world!')
    assert hw_rva >= 0x1000
    assert (hw_rva & 0xFFF) < 0x100
    zlx.io.omsg('hello_msg offset: {:X}', hw_rva)
    zlx.io.bin_save(output_path, image)
    return

def windump_info (input_path):
    import zlx.windump
    import zlx.io
    with open(input_path, 'rb') as f:
        dh = zlx.windump.parse_header(f)
    print(repr(dh))
    return

def msf7_info (input_path):
    import zlx.msf7
    mr = zlx.msf7.reader(input_path)
    print(repr(mr.superblock))
    mr.load_dir()
    print('dir blocks: {!r}'.format(mr.dir_blocks))
    print('stream count: {}'.format(mr.stream_count))
    print('stream sizes: {!r}'.format(mr.stream_size_table))
    print('stream #1:\n{}'.format(zlx.bin.hex_char_dump(mr.streams[1])))

def xref_test ():
    import zlx.bin
    import zlx.wire
    x = zlx.bin.xref_scan(b'\xE8\x0B\0\0\0\xB8\x10\x10\0\0------X\xFA\xFF\xFF\xFF!',
            target = 0x1010,
            encoder = lambda v: zlx.wire.u32le.encode_to_bytes(v & 0xFFFFFFFF),
            base = 0x1000, rel_delta_range = range(4, 6))
    print('{!r}'.format(x))

def inc_build_no_test ():
    from zlx.build_number import inc as increment_build_number
    x = increment_build_number('ala\nbala\nBUILD =           	123; # gr\nxx;')
    print(repr(x))
    assert x == 'ala\nbala\nBUILD =           	124; # gr\nxx;\n'

if __name__ == '__main__':
    print(repr(sys.argv))
    if len(sys.argv) >= 2:
        if sys.argv[1] == 'map-pe':
            map_pe(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == 'windump-info':
            windump_info(sys.argv[2])
        elif sys.argv[1] == 'msf7-info':
            msf7_info(sys.argv[2])
    else:
        var = None
        for var in sorted(filter(lambda n: n.endswith('_test'), globals())):
            print('calling test {!r}'.format(var))
            globals()[var]()

        #io_test()
        #record_test()
        #wire_test()
        #hex_char_dump_test()
        #pe_test()

