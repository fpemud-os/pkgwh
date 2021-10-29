
import re
from snakeoil import klass


def is_valid_category(s):
    assert isinstance(s, str)
    return _category_name_re.fullmatch(s)


def is_valid_package_name(s):
    assert isinstance(s, str)
    return _package_name_re.fullmatch(s)


class CP(klass.SlotsPicklingMixin, metaclass=klass.immutable_instance):
    """category/package, which represents a specific Gentoo package

    :ivar category: str category name
    :ivar package: str package name
    :ivar cp_str: str category/package
    """

    __slots__ = ("category", "package")

    def __init__(self, *args, _do_check=True):
        """
        Can be called with one string or with two string args.

        If called with one arg that is the "category/package" string.

        If called with two args they are the category and package components respectively.

        _do_check=False is for internal use only, to raise performance
        """

        if len(args) == 1:
            assert _do_check
            try:
                category, pkgname = args[0].rsplit("/", 1)
            except ValueError:
                raise TypeError("no category component")     # occurs if the rsplit yields only one item
        elif len(args) == 2:
            if _do_check:
                if any([not isinstance(x, str) for x in args]):
                    raise TypeError(f"all args must be strings, got {args!r}")

            category = args[0]
            pkgname = args[1]

            if _do_check:
                if not is_valid_category(category):
                    raise TypeError("invalid category component")
                if not is_valid_package_name(pkgname):
                    raise TypeError("invalid package component")
        else:
            raise TypeError(f"CP takes category/package string or separate components as arguments: got {args!r}")

        sf = object.__setattr__
        sf(self, 'category', category)
        sf(self, 'package', pkgname)

    @property
    def cp_str(self):
        return self.category + "/" + self.package

    def __hash__(self):
        return hash(self._all_attrs())

    def __repr__(self):
        return '<%s key=%s @%#8x>' % (self.__class__.__name__, self.cp_str, id(self))

    def __str__(self):
        return self.cp_str

    def __eq__(self, other):
        return isinstance(other, CP) and self._all_attrs() == other._all_attrs()

    def __ne__(self, other):
        return not self.__eq__(other)

    def _all_attrs(self):
        return (self.category, self.package)


class InvalidCP(ValueError):
    """CP with unsupported characters or format."""

    def __init__(self, cp_str, err=None):
        self.atom = cp_str
        self.err = err
        super().__init__(str(self))

    def __str__(self):
        msg = f'invalid CP: {self.cp_str!r}'
        if self.err is not None:
            msg += f': {self.err}'
        return msg


_category_name_re = re.compile(r"^(?:[a-zA-Z0-9][-a-zA-Z0-9+._]*(?:/(?!$))?)+$")                       # FIXME: change to lazy+compile + weak-ref, snakeoil.demandload.demand_compile_regexp() doesn't have variable form

_package_name_re = re.compile(r"^[a-zA-Z0-9+_]+$")                                                     # FIXME: change to lazy+compile + weak-ref? test performance first
