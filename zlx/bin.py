import struct
import sys
import zlx.int
import zlx.wire

if sys.version_info[0] >= 3:
    from io import StringIO
else:
    from StringIO import StringIO

NO_OFFSET = -1
PLAIN_OFFSET = 128
GROUP_4_OFFSET = 4

NO_HEX = None

NO_CHARS = None
PRINTABLE_ASCII_CHARS_MAP = tuple('.' if n < 0x20 or n >= 0x7F else chr(n) for n in range(256))

OFFSET_8HEX = lambda n: '{:08X}: '.format(n)
OFFSET_HIDE = lambda n: ''

def byte_as_printable_ascii_char_printer (data, offset):
    return (PRINTABLE_ASCII_CHARS_MAP[data[offset]], 1)

def hex_char_dump (
        data,
        data_offset = 0,
        data_length = None,
        display_data_offset = None,
        display_row_offset = None,
        display_row_count = None,
        offset_printer = None,
        char_printer = byte_as_printable_ascii_char_printer,
        width = 0x10,
        line_prefix = '',
        line_suffix = '\n',
        offset_suffix = ': ',
        mod_sep = { 1: ' ', 4: '  ' },
        hex_char_sep = '    ',
        no_data_pad = '..',
        no_char_pad = ' ',
        ):

    if isinstance(data, (bytes, bytearray)):
        data = zlx.wire.stream(data, 'u8').u8

    if data_length is None:
        data_length = len(data) - data_offset

    if display_data_offset is None:
        display_data_offset = data_offset
    if display_row_offset is None:
        display_row_offset = display_data_offset - display_data_offset % width
    if display_row_count is None:
        items_in_first_row = width - (display_data_offset - display_row_offset)
        display_row_count = 1
        if data_length > items_in_first_row:
            display_row_count += (data_length - items_in_first_row + width - 1) // width

    if offset_printer is None:
        last_offset = display_data_offset + (display_row_count - 1) * width
        offset_digits = (zlx.int.log2_ceil(last_offset) + 3) // 4

        offset_printer = lambda x, fmt='{{:0{}X}}: '.format(offset_digits): fmt.format(x)

    offset_delta = data_offset - display_data_offset
    o = StringIO()
    for r in range(display_row_count):
        o.write(offset_printer(display_row_offset + r * width))
        for c in range(width):
            offset = display_row_offset + r * width + c + offset_delta
            if c > 0:
                for b in sorted(mod_sep.keys(), reverse=True):
                    if c % b == 0:
                        o.write(mod_sep[b])
                        break
            if offset < data_offset or offset >= data_offset + data_length:
                o.write(no_data_pad)
            else:
                o.write('{:02X}'.format(data[offset]))
        o.write(hex_char_sep)
        inc = 1
        for c in range(width):
            inc -= 1
            if inc > 0: next
            offset = display_row_offset + r * width + c + offset_delta
            if offset < data_offset or offset >= data_offset + data_length:
                o.write(no_char_pad)
            else:
                s, inc = char_printer(data, offset)
                o.write(s)
        o.write('\n')

    return o.getvalue()

xref_collection = zlx.record.make('xrefs', 'absolute relative')

def xref_scan (data, target, encoder, base = 0, 
        start_offset = 0, end_offset = None,
        abs_ref = True, rel_delta_range = range(0, 1)):
    if end_offset is None: end_offset = len(data)
    xrefs = xref_collection([], {})
    if abs_ref:
        encoded_target = encoder(target)
        offset = start_offset
        while True:
            offset = data.find(encoded_target, offset, end_offset)
            if offset < 0: break
            xrefs.absolute.append(offset)
            offset += 1
    if rel_delta_range:
        for offset in range(start_offset, end_offset):
            for delta in rel_delta_range:
                encoded_target = encoder(target - base - delta - offset)
                print('checking for {!r} at offset {!r} where {!r} is'.format(encoded_target, offset, data[offset : offset + len(encoded_target)]))
                if data[offset : offset + len(encoded_target)] == encoded_target:
                    if delta not in xrefs.relative:
                        xrefs.relative[delta] = []
                    xrefs.relative[delta].append(offset)
    return xrefs

