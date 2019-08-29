import zlx.record
import zlx.bin
import zlx.io
import zlx.wire
import zlx.int

MZ_MAGIC = 0x5A4D
PE_MAGIC = 0x4550

MACHINE_I386 = 0x014C
MACHINE_IA64 = 0x0200
MACHINE_AMD64 = 0x8664

# header flags
FH_RELOCS_STRIPPED = 0x0001
FH_EXECUTABLE_IMAGE = 0x0002
FH_LINE_NUMS_STRIPPED = 0x0004
FH_LOCAL_SYMS_STRIPPED = 0x0008
FH_AGGRESSIVE_WS_TRIM = 0x0010
FH_LARGE_ADDRESS_AWARE = 0x0020
FH_BYTES_REVERSED_LO = 0x0080
FH_32BIT_MACHINE = 0x0100
FH_DEBUG_STRIPPED = 0x0200
FH_REMOVABLE_RUN_FROM_SWAP = 0x0400
FH_NET_RUN_FROM_SWAP = 0x0800
FH_SYSTEM = 0x1000
FH_DLL = 0x2000
FH_UP_SYSTEM_ONLY = 0x4000
FH_BYTES_REVERSED_HI = 0x8000

OPT_HDR32_MAGIC = 0x010B
OPT_HDR64_MAGIC = 0x020B
ROM_OPT_HDR_MAGIC = 0x0107

SUBSYSTEM_UNKNOWN = 0
SUBSYSTEM_NATIVE = 1
SUBSYSTEM_WINDOWS_GUI = 2
SUBSYSTEM_WINDOWS_CUI = 3
SUBSYSTEM_OS2_CUI = 5
SUBSYSTEM_POSIX_CUI = 7
SUBSYSTEM_WINDOWS_CE_GUI = 9
SUBSYSTEM_EFI_APPLICATION = 10
SUBSYSTEM_EFI_BOOT_SERVICE_DRIVER = 11
SUBSYSTEM_EFI_RUNTIME_DRIVER = 12
SUBSYSTEM_EFI_ROM = 13
SUBSYSTEM_XBOX = 14
SUBSYSTEM_WINDOWS_BOOT_APPLICATION = 16

MZHeader = zlx.record.make('MZHeader', 'magic e_lfanew')

def parse_mz_header (ba):
    return MZHeader(ba.u16le[0], ba.u32le[0x3C])

FileHeader = zlx.record.make('FileHeader', '''
        machine section_count timestamp symbol_table_offset symbol_count
        opt_hdr_size flags''')
FileHeader.SIZE = 0x14

PEHeader = zlx.record.make('PEHeader', 'magic file_hdr opt_hdr sec')
OptionalHeader32 = zlx.record.make('OptionalHeader32', '''
        magic
        major_linker_version
        minor_linker_version
        size_of_code
        size_of_initialized_data
        size_of_uninitialized_data
        entry_point
        base_of_code
        base_of_data
        image_base
        section_alignment
        file_alignment
        major_operating_system_version
        minor_operating_system_version
        major_image_version
        minor_image_version
        major_subsystem_version
        minor_subsystem_version
        win32_version_value
        size_of_image
        size_of_headers
        checksum
        subsystem
        dll_characteristics
        size_of_stack_reserve
        size_of_stack_commit
        size_of_heap_reserve
        size_of_heap_commit
        loader_flags
        dir_count
        dir
        ''')

OptionalHeader64 = zlx.record.make('OptionalHeader64', '''
        magic
        major_linker_version
        minor_linker_version
        size_of_code
        size_of_initialized_data
        size_of_uninitialized_data
        address_of_entry_point
        base_of_code
        image_base
        section_alignment
        file_alignment
        major_operating_system_version
        minor_operating_system_version
        major_image_version
        minor_image_version
        major_subsystem_version
        minor_subsystem_version
        win32_version_value
        size_of_image
        size_of_headers
        check_sum
        subsystem
        dll_characteristics
        size_of_stack_reserve
        size_of_stack_commit
        size_of_heap_reserve
        size_of_heap_commit
        loader_flags
        dir_count
        dir
        ''')

UnknownOptionalHeader = zlx.record.make('UnknownOptionalHeader', 'magic')

DataDirectory = zlx.record.make('DataDirectory', 'rva size')

SectionHeader = zlx.record.make('SectionHeader', '''
        name vsize rva fsize fpos
        reloc_fpos line_fpos reloc_count line_count flags''')

def parse_file_header (ba, offset):
    return FileHeader(
        machine                 = ba.u16le[offset + 0x00],
        section_count           = ba.u16le[offset + 0x02],
        timestamp               = ba.u32le[offset + 0x04],
        symbol_table_offset     = ba.u32le[offset + 0x08],
        symbol_count            = ba.u32le[offset + 0x0C],
        opt_hdr_size            = ba.u16le[offset + 0x10],
        flags                   = ba.u16le[offset + 0x12])

def parse_data_directory (ba, offset):
    return DataDirectory(rva = ba.u32le[offset], size = ba.u32le[offset + 4])

def parse_optional_header32 (ba, offset):
    oh = OptionalHeader32(
        magic                           = ba.u16le[offset + 0x00],
        major_linker_version            = ba. u8  [offset + 0x02],
        minor_linker_version            = ba. u8  [offset + 0x03],
        size_of_code                    = ba.u32le[offset + 0x04],
        size_of_initialized_data        = ba.u32le[offset + 0x08],
        size_of_uninitialized_data      = ba.u32le[offset + 0x0C],
        entry_point                     = ba.u32le[offset + 0x10],
        base_of_code                    = ba.u32le[offset + 0x14],
        base_of_data                    = ba.u32le[offset + 0x18],
        image_base                      = ba.u32le[offset + 0x1C],
        section_alignment               = ba.u32le[offset + 0x20],
        file_alignment                  = ba.u32le[offset + 0x24],
        major_operating_system_version  = ba.u16le[offset + 0x28],
        minor_operating_system_version  = ba.u16le[offset + 0x2A],
        major_image_version             = ba.u16le[offset + 0x2C],
        minor_image_version             = ba.u16le[offset + 0x2E],
        major_subsystem_version         = ba.u16le[offset + 0x30],
        minor_subsystem_version         = ba.u16le[offset + 0x32],
        win32_version_value             = ba.u32le[offset + 0x34],
        size_of_image                   = ba.u32le[offset + 0x38],
        size_of_headers                 = ba.u32le[offset + 0x3C],
        checksum                        = ba.u32le[offset + 0x40],
        subsystem                       = ba.u16le[offset + 0x44],
        dll_characteristics             = ba.u16le[offset + 0x46],
        size_of_stack_reserve           = ba.u32le[offset + 0x48],
        size_of_stack_commit            = ba.u32le[offset + 0x4C],
        size_of_heap_reserve            = ba.u32le[offset + 0x50],
        size_of_heap_commit             = ba.u32le[offset + 0x54],
        loader_flags                    = ba.u32le[offset + 0x58],
        dir_count                       = ba.u32le[offset + 0x5C])
    oh.dir = tuple(parse_data_directory(ba, offset + 0x60 + 8 * i) for i in range(16))
    return oh

def parse_optional_header64 (ba, offset):
    oh = OptionalHeader64(
        magic                           = ba.u16le[offset + 0x00],
        major_linker_version            = ba. u8  [offset + 0x02],
        minor_linker_version            = ba. u8  [offset + 0x03],
        size_of_code                    = ba.u32le[offset + 0x04],
        size_of_initialized_data        = ba.u32le[offset + 0x08],
        size_of_uninitialized_data      = ba.u32le[offset + 0x0C],
        address_of_entry_point          = ba.u32le[offset + 0x10],
        base_of_code                    = ba.u32le[offset + 0x14],
        image_base                      = ba.u64le[offset + 0x18],
        section_alignment               = ba.u32le[offset + 0x20],
        file_alignment                  = ba.u32le[offset + 0x24],
        major_operating_system_version  = ba.u16le[offset + 0x28],
        minor_operating_system_version  = ba.u16le[offset + 0x2A],
        major_image_version             = ba.u16le[offset + 0x2C],
        minor_image_version             = ba.u16le[offset + 0x2E],
        major_subsystem_version         = ba.u16le[offset + 0x30],
        minor_subsystem_version         = ba.u16le[offset + 0x32],
        win32_version_value             = ba.u32le[offset + 0x34],
        size_of_image                   = ba.u32le[offset + 0x38],
        size_of_headers                 = ba.u32le[offset + 0x3C],
        checksum                        = ba.u32le[offset + 0x40],
        subsystem                       = ba.u16le[offset + 0x44],
        dll_characteristics             = ba.u16le[offset + 0x46],
        size_of_stack_reserve           = ba.u32le[offset + 0x48],
        size_of_stack_commit            = ba.u64le[offset + 0x50],
        size_of_heap_reserve            = ba.u64le[offset + 0x58],
        size_of_heap_commit             = ba.u64le[offset + 0x60],
        loader_flags                    = ba.u32le[offset + 0x68],
        dir_count                       = ba.u32le[offset + 0x6C])
    oh.dir = tuple(parse_data_directory(ba, offset + 0x60 + 8 * i) for i in range(16))
    return oh

def parse_optional_header (ba, offset):
    opt_hdr_magic = ba.u16le[offset]
    if opt_hdr_magic == OPT_HDR32_MAGIC:
        oh = parse_optional_header32(ba, offset)
    elif opt_hdr_magic == OPT_HDR64_MAGIC:
        oh = parse_optional_header64(ba, offset)
    else:
        oh = UnknownOptionalHeader(opt_hdr_magic)
    return oh

def parse_section_header (ba, offset):
    return SectionHeader(
        name = ba[offset, 8],
        vsize = ba.u32le[offset + 0x08],
        rva = ba.u32le[offset + 0x0C],
        fsize = ba.u32le[offset + 0x10],
        fpos = ba.u32le[offset + 0x14],
        reloc_fpos = ba.u32le[offset + 0x18],
        line_fpos = ba.u32le[offset + 0x1C],
        reloc_count = ba.u16le[offset + 0x20],
        line_count = ba.u16le[offset + 0x22],
        flags = ba.u32le[offset + 0x24])

def parse_pe_header (ba, offset):
    peh = PEHeader(magic = ba.u32le[offset])
    peh.file_hdr = parse_file_header(ba, offset + 4)
    peh.opt_hdr = parse_optional_header(ba, offset + 24)
    peh.sec = tuple(
        parse_section_header(ba,
            offset + 0x18 + peh.file_hdr.opt_hdr_size + i * 0x28)
        for i in range(peh.file_hdr.section_count))
    return peh

def map_parsed_pe (ba, peh, arch_page_size = 4096):
    if not isinstance(ba, zlx.wire.stream): ba = zlx.wire.stream(ba)
    align = peh.opt_hdr.section_alignment if zlx.int.pow2_check(peh.opt_hdr.section_alignment) else arch_page_size
    falign = peh.opt_hdr.file_alignment if zlx.int.pow2_check(peh.opt_hdr.file_alignment) else 1
    image_align = max(align, arch_page_size)
    image = bytearray(zlx.int.pow2_round_up(peh.opt_hdr.size_of_image, image_align))
    hsize = peh.opt_hdr.size_of_headers
    image[0:hsize] = ba[0, hsize]
    for sec in peh.sec:
        if align >= arch_page_size: 
            rva = zlx.int.pow2_round_down(sec.rva, align)
            fpos = zlx.int.pow2_round_down(sec.fpos, falign)
        else:
            rva = sec.rva
            fpos = sec.fpos
        size = min(sec.vsize, sec.fsize) if sec.vsize > 0 else sec.fsize
        if size > 0:
            image[rva:rva+size] = ba[fpos, size]

    return image

def map_pe_from_path (path, arch_page_size = 4096):
    ba = zlx.wire.stream(zlx.io.bin_load(path))
    mzh = parse_mz_header(ba)
    peh = parse_pe_header(ba, offset = mzh.e_lfanew)
    return map_parsed_pe(ba, peh, arch_page_size)

