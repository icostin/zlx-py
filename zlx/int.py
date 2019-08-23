import sys

if sys.version_info[0] >= 3:
    INT_TYPES = (int,)
else:
    INT_TYPES = (int, long)

def pow2_check (n):
    return n > 0 and (n & (n - 1)) == 0

def pow2_round_down (n, p):
    assert pow2_check(p)
    return n & ~(p - 1)

def pow2_round_up (n, p):
    assert pow2_check(p)
    return (n + p - 1) & ~(p - 1)

def hex (n, prefix='0x', suffix=''):
    return '{}{:X}{}'.format(prefix, n, suffix)

def log2_ceil (n):
    p = 0
    while n > (1 << p): p += 1
    return p

def hex_items (l, sep = ', ', prefix='', suffix='', item_prefix='0x', item_suffix=''):
    return ''.join((prefix, sep.join(hex(n, prefix=item_prefix, suffix=item_suffix) for n in l), suffix))

def u8_hex (n):
    return '{:02X}'.format(n)

def u16_hex (n):
    return '{:04X}'.format(n)

def u32_hex (n):
    return '{:04X}'.format(n)

def u64_hex (n):
    return '{:04X}'.format(n)

def u8_in_range (n):
    return n >= 0 and n < 0x100

def u8_trunc (n):
    return n & 0xFF

def u8_add (a, b):
    return (a + b) & 0xFF
