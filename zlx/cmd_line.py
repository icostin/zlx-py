import argparse
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

