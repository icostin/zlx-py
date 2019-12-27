from __future__ import absolute_import
import argparse
import io
import sys
import traceback
import zlx.record
import zlx.io

sfmt = zlx.io.sfmt
omsg = zlx.io.omsg
emsg = zlx.io.emsg
dmsg = zlx.io.dmsg

def cmd_help (req):
    req.ap.print_help()

def cmd_map_pe (req):
    import zlx.pe
    n = 0
    for input_path in req.FILE:
        output_path = req.out_spec.format(path=input_path, index=n)
        image = zlx.pe.map_pe_from_path(input_path, req.page_size)
        zlx.io.bin_save(output_path, image)
        n += 1

def cmd_msf7_info (req):
    import zlx.msf7
    for input_path in req.FILE:
        try:
            mr = zlx.msf7.reader(input_path)
            omsg('{!r}:', input_path)
            omsg(' superblock:')
            omsg('  magic:                  {!r}', mr.superblock.magic)
            omsg('  block size:             {}', mr.superblock.block_size)
            omsg('  free block map block:   {}', mr.superblock.free_block_map_block)
            omsg('  block count:            {}', mr.superblock.block_count)
            omsg('  dir size:               {}', mr.superblock.dir_size)
            omsg('  something:              {}', mr.superblock.suttin)
            omsg('  dir block map block:    {}', mr.superblock.dir_block_map_block)

            omsg(' directory:')
            mr.load_dir()
            omsg('  stream count:           {}', mr.stream_count)

            omsg(' streams:')
            for i in range(mr.stream_count):
                omsg('  {:03}: size={:<7}', i, mr.stream_size_table[i])
        except Exception as e:
            emsg('error processing file {!r}', input_path)
            raise

def cmd_inc_build (req):
    from zlx.build_number import inc
    for path in req.FILE:
        inc(path = path, save_path = path, pattern = req.prefix)

def cmd_test_stream_cache (req):
    with open(req.FILE, 'rb') as f:
        sc = zlx.io.stream_cache(f,
                align = req.alignment,
                assume_size = req.assume_size)
        for c in req.commands:
            dmsg('*** {!r}', sc)
            cparts = c.split(':')
            verb = cparts[0]
            args = cparts[1:]
            if verb == 'get':
                ofs, size = (int(x) for x in args)
                dmsg('--- get(offset={}, size={})', ofs, size)
                blk_list = sc.get(ofs, size)
                dmsg('==> block: {!r}', blk_list)
            elif verb == 'load':
                ofs, size = (int(x) for x in args)
                dmsg('--- load(offset={}, size={})', ofs, size)
                sc.load(ofs, size)
            else:
                raise RuntimeError(sfmt('unsupported verb {!r}', verb))
        dmsg('*** {!r}', sc)

def cmd_test_mth (req):
    import zlx.mth
    zlx.mth.self_test()
    if req.verbose:
        omsg('zlx.mth test passed!')

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

def cmd_test (req):
    var = None
    tests = filter(lambda n: n.endswith('_test') and not n.startswith('cmd_'), globals())
    tests = sorted(tests)
    for var in tests:
        print('calling test {!r}'.format(var))
        globals()[var]()

def main (args):
    ap = argparse.ArgumentParser(
            description='tool to process binary and text data')
    ap.add_argument('-V', '--version', action='version', version='zlx {}'.format(zlx.VER_STR))
    ap.add_argument('-v', '--verbose', help='be verbose',
            action='store_true', default=False)

    sp = ap.add_subparsers(title='subcommands', dest='cmd')

    p = sp.add_parser('help')
    p = sp.add_parser('msf7-info',
            help='provides information about MSF v7 files')
    p.add_argument('FILE', nargs='*', help='file(s) to process')

    p = sp.add_parser('map-pe', help='creates an image of the mapped PE file')
    p.add_argument('FILE', nargs='*', help='input file(s)')
    p.add_argument('-o', '--out', dest='out_spec', default='{path}.img')
    p.add_argument('-p', '--page-size', dest='page_size', type=int, default=4096)

    p = sp.add_parser('inc-build',
            help = 'increments build number in a given file')
    p.add_argument('-p', '--prefix', dest = 'prefix', help='prefix string for the build number', default = 'BUILD =')
    p.add_argument('FILE', nargs='*', help='file(s)')

    p = sp.add_parser('test',
            help = 'runs all tests with default parameters')

    p = sp.add_parser('test-stream-cache',
            help = 'test drives zlx.io.stream_cache')
    p.add_argument('FILE',
            help = 'input file')
    p.add_argument('-a', '--alignment',
            type = int,
            help = 'alignment for load commands',
            default = 4096)
    p.add_argument('-z', '--assume-size',
            type = int,
            help='init caching to assume the given size',
            default = None)
    p.add_argument('commands',
            nargs = '*',
            help = '"get:<offset>:<size>" or "load:<offset>:<size>"')

    p = sp.add_parser('test-mth',
            help = 'tests zlx.mth module')

    req = ap.parse_args(args[1:])
    if req.verbose:
        print('command line: {!r}'.format(req))

    if req.cmd is None: req.cmd = 'help'
    dmsg('parsed command line: {}', req)

    req.ap = ap

    globals()['cmd_' + req.cmd.replace('-', '_')](req)

def entry ():
    main(sys.argv)

