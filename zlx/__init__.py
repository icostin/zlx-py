import sys

VER = 0

def sfmt (fmt, *a, **b):
    return fmt.format(*a, **b)


def omsg (fmt, *a, **b):
    sys.stdout.write(fmt.format(*a, **b) + '\n')

def emsg (fmt, *a, **b):
    sys.stdout.write(fmt.format(*a, **b) + '\n')

def err (fmt, *a, **b):
    raise RuntimeError(sfmt(fmt, *a, **b))

