
class Record(object):
    def __init__ (self, *a, **b):
        for i in range(len(a)):
            setattr(self, self.__slots__[i], a[i])
        for i in range(len(a), len(self.__slots__)):
            setattr(self, self.__slots__[i], None)
        for k, v in b.items():
            setattr(self, k, v)
        return

    def to_tuple (self):
        return (getattr(self, field) for field in self.__slots__)

    def __repr__ (self):
        return '{}{{{}}}'.format(self.__class__.__name__, ', '.join('{}={}'.format(k, repr(getattr(self, k))) for k in self.__slots__))
    pass # Record

def make (name, fields, validators = None, field_names = None):
    fields = tuple(fields.split())
    if validators is None: validators = {}
    if field_names is None: field_names = {}
    f2n = { f: field_names[f] if f in field_names else f for f in fields }
    n2f = { n: f for f, n in f2n.items() }
    t = type(name, (Record,), {'__slots__': fields, '_field_to_name': f2n, '_name_to_field': n2f})
    for f in fields:
        v = validators[f] if f in validators else lambda self: True
        setattr(t, 'validate_{}'.format(f), lambda self: v(getattr(self, f)))
    return t

