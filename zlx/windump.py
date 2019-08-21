import zlx.record
import zlx.bin
import zlx.int

DUMP32_MAGIC = b'PAGEDUMP'
DUMP64_MAGIC = b'PAGEDU64'

Header = zlx.record.make('WinDumpHeader', '''
    magic
    ver_major
    ver_minor
    dir_table_base
    pfn_database
    loaded_module_list
    active_process_head
    machine_image_type
    cpu_count
    bug_check_code
    bug_check_params
    debugger_data_block
    phys_mem_blocks
    exc
    dump_type
    raw_system_up_time
    raw_system_time
    ''',
    field_repr = dict(
        dir_table_base = zlx.int.hex,
        pfn_database = zlx.int.hex,
        loaded_module_list = zlx.int.hex,
        active_process_head = zlx.int.hex,
        machine_image_type = zlx.int.hex,
        bug_check_code = zlx.int.hex,
        bug_check_params = lambda x: zlx.int.hex_items(x, sep=', ', prefix='(', suffix=')'),
        debugger_data_block = zlx.int.hex,
        ))

def parse_header (data):
    if isinstance(data, zlx.bin.io_accessor): ba = data
    else: ba = zlx.bin.io_accessor(data)
    h = Header(magic = ba[0, 8])
    if h.magic == DUMP32_MAGIC:
        h.ver_major = ba.u32le[0x08]
        h.ver_minor = ba.u32le[0x0C]
    elif h.magic == DUMP64_MAGIC:
        h.ver_major = ba.u32le[0x08]
        h.ver_minor = ba.u32le[0x0C]
        h.dir_table_base = ba.u64le[0x10]
        h.pfn_database = ba.u64le[0x18]
        h.loaded_module_list = ba.u64le[0x20]
        h.active_process_head = ba.u64le[0x28]
        h.machine_image_type = ba.u32le[0x30]
        h.cpu_count = ba.u32le[0x34]
        h.bug_check_code = ba.u32le[0x38]
        h.bug_check_params = ba.u64le[0x40, 4]
        h.debugger_data_block = ba.u64le[0x80]
    return h

