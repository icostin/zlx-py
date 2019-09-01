import argparse
import sys
import traceback
import zlx.record
import zlx.io

omsg = zlx.io.omsg
emsg = zlx.io.emsg

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

def main (args):
    ap = argparse.ArgumentParser(
            description='tool to process binary and text data')
    ap.add_argument('-v', '--verbose', help='be verbose',
            action='store_true', default=False)

    sp = ap.add_subparsers(title='subcommands', dest='cmd')

    p = sp.add_parser('help')
    p = sp.add_parser('msf7-info',
            help='provides information about MSF v7 files')
    p.add_argument('FILE', nargs='*', help='file(s) to process')

    p = sp.add_parser('map-pe', help='creates an image of the mapped PE file')
    p.add_argument('FILE', nargs='*', help='input file(s)')
    p.add_argument('-o OUTSPEC', dest='out_spec', default='{path}.img')
    p.add_argument('-p PAGESIZE', dest='page_size', type=int, default=4096)

    req = ap.parse_args(args[1:])
    if req.verbose:
        print('command line: {!r}'.format(req))

    if req.cmd is None: req.cmd = 'help'
    req.ap = ap

    globals()['cmd_' + req.cmd.replace('-', '_')](req)

def entry ():
    main(sys.argv)

