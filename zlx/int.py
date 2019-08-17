
def pow2_check (n):
    return n > 0 and (n & (n - 1)) == 0

def pow2_round_down (n, p):
    assert pow2_check(p)
    return n & ~(p - 1)

def pow2_round_up (n, p):
    assert pow2_check(p)
    return (n + p - 1) & ~(p - 1)

def u8_in_range (n):
    return n >= 0 and n < 0x100

def u8_trunc (n):
    return n & 0xFF

def u8_add (a, b):
    return (a + b) & 0xFF
