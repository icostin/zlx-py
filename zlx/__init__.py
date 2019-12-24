import sys

VER_MAJOR = 0
VER_MINOR = 0
BUILD = 13

VER = (VER_MAJOR, VER_MINOR, BUILD)

VER_STR = '{}.{}.{}'.format(*VER)

def sfmt (fmt, *a, **b):
    return fmt.format(*a, **b)

def omsg (fmt, *a, **b):
    sys.stdout.write(fmt.format(*a, **b) + '\n')

def emsg (fmt, *a, **b):
    sys.stdout.write(fmt.format(*a, **b) + '\n')

def err (fmt, *a, **b):
    raise RuntimeError(sfmt(fmt, *a, **b))

