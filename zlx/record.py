
class Record (object):

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

    def _repr_field (self, field_name):
        field_value = getattr(self, field_name)
        if field_name in self._field_repr:
            return self._field_repr[field_name](field_value)
        return repr(field_value)

    def __repr__ (self):
        return '{}{{{}}}'.format(self.__class__.__name__, ', '.join('{}={}'.format(k, self._repr_field(k)) for k in self.__slots__))

    @classmethod
    def from_io_accessor (ty, ioa, offset):
        o = offset
        v = []
        for field in ty.__slots__:
            a, l = getattr(ioa, ty._field_acc[field]).unpack(o)
            o += l
            v.append(a)
        r = ty(*v)
        return (r, o - offset)

# Record

def make (name, fields, field_names = None, field_repr = None):
    if isinstance(fields, str):
        fields = tuple(fields.split())
    if field_names is None: field_names = {}
    if field_repr is None: field_repr = {}
    f2n = { f: field_names[f] if f in field_names else f for f in fields }
    n2f = { n: f for f, n in f2n.items() }
    t = type(name, (Record,), dict(
        __slots__ = fields,
        _field_to_name = f2n,
        _name_to_field = n2f,
        _field_repr = field_repr))
    return t

