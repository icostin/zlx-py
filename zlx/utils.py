from __future__ import absolute_import
import traceback
import os

def sfmt (fmt, *l, **kw): return fmt.format(*l, **kw)

dlog_path = os.environ.get('ZLX_LOG', '')
if dlog_path:
    dlog = open(dlog_path, 'w') if dlog_path != '-' else sys.stderr
    def dmsg (fmt, *l, **kw):
        ff = traceback.extract_stack()
        src, line, fn, etc = ff[len(ff) - 2]

        dlog.write(('{}:{}: in {}():' + fmt + '\n').format(src, line, fn, *l, **kw))
        dlog.flush()
else:
    def dmsg (fmt, *l, **kw): pass

def omsg (fmt, *l, **kw):
    return sys.stdout.write((fmt + '\n').format(*l, **kw))

def emsg (fmt, *l, **kw):
    return sys.stderr.write((fmt + '\n').format(*l, **kw))
