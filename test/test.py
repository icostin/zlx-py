import sys

def bin_test ():
    import zlx.bin
    a = zlx.bin.accessor(b'\xF0\xF1\xF2\xF3\xF4\xF5\xF6\xF7\xF8\xF9', disp = 1, length = 8)
    assert a.u8[1] == 0xF2
    assert a.i8[1] == -14
    return

def record_test ():
    import zlx.record
    import zlx.int
    P = zlx.record.make('Point', 'x y', validators=dict(int=zlx.int.u8_in_range))
    p = P(1, 2)
    print(repr(p))
    print(p.validate_x())

def pe_test ():
    import zlx.bin
    import zlx.pe
    ba = zlx.bin.accessor(b'MZ\0\0xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\x80\0\0\0')
    x = zlx.pe.parse_mz_header(ba)
    print(repr(x))
    assert x.magic == zlx.pe.MZ_MAGIC
    assert x.e_lfanew == 0x80

def map_pe (input_path, output_path):
    import zlx.io
    import zlx.bin
    import zlx.pe
    ba = zlx.bin.accessor(zlx.io.bin_load(input_path))
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

if __name__ == '__main__':
    print(repr(sys.argv))
    if len(sys.argv) >= 2 and sys.argv[1] == 'map-pe':
        map_pe(sys.argv[2], sys.argv[3])
    else:
        bin_test()
        record_test()
        pe_test()

