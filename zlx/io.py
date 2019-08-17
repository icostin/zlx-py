import sys
import io

def omsg (fmt, *l, **kw):
    return sys.stdout.write((fmt + '\n').format(*l, **kw))

def bin_load (path):
    with open(path, 'rb') as f:
        return f.read()

def bin_save (path, content):
    with open(path, 'wb') as f:
        return f.write(content)

def txt_load (path):
    with open(path, 'r') as f:
        return f.read()

def txt_save (path, content):
    with open(path, 'w') as f:
        return f.write(content)

