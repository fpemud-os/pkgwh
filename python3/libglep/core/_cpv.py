#!/usr/bin/env python3

import re
from snakeoil import klass
from ._cp import is_valid_category, is_valid_package_name


def is_valid_package_version(s):
    assert isinstance(s, str)
    return _package_version_re.fullmatch(s)


def is_valid_package_revision(s):
    assert isinstance(s, str)
    if len(s) == 0:
        return False
    if s[0] != 'r':
        return False
    try:
        if int(s[1:]) < 1:
            return False
    except ValueError:
        return False
    return True


class CPV(klass.SlotsPicklingMixin, metaclass=klass.immutable_instance):
    """category/package-version or category/package-version-revision, which represents one version of a specific Gentoo package

    :ivar category: str category name
    :ivar package: str package name
    :ivar ver: str version
    :ivar rev: str revision, optional
    :ivar fullver: str version-revision
    :ivar cp_str: str category/package
    :ivar cpv_str: str category/package-version-revision
    """

    __slots__ = ("category", "package", "ver", "rev")

    def __init__(self, *args, _do_check=True):
        """
        Can be called with one string arg, three string args or four string args.

        If called with one arg that is the "category/package-version" or "category/package-version-revision" string.

        If called with three args they are the category, package and version components respectively. For four args, the revision components is the fourth arg.

        _do_check=False is for internal use only, to raise performance
        """

        if len(args) == 1:
            assert _do_check
            try:
                category, pkg_name_ver = args[0].rsplit("/", 1)
            except ValueError:
                raise TypeError("no category component")     # occurs if the rsplit yields only one item
            pkg_chunks = pkg_name_ver.split("-")
            if len(pkg_chunks) < 2:
                raise TypeError("missing package name, version, and/or revision")
            pkgname = pkg_chunks[0]
            if is_valid_package_revision(pkg_chunks[-1]):
                ver = "-".join(pkg_chunks[1:-1])
                rev = pkg_chunks[-1]
            else:
                ver = pkg_chunks[1:]
                rev = None
        elif len(args) == 3 or len(args) == 4:
            if _do_check:
                if any([not isinstance(x, str) for x in args]):
                    raise TypeError(f"all args must be strings, got {args!r}")

            category = args[0]
            pkgname = args[1]
            ver = args[2]
            rev = args[3] if len(args) > 3 else None
                
            if _do_check:
                if not is_valid_category(category):
                    raise TypeError("invalid category component")
                if not is_valid_package_name(pkgname):
                    raise TypeError("invalid package component")
                if not is_valid_package_version(ver):
                    raise TypeError("invalid version component")
                if rev is not None:
                    if not is_valid_package_revision(rev):
                        raise TypeError("invalid revision component")
        else:
            raise TypeError(f"CPV takes cpv string or separate components as arguments: got {args!r}")

        sf = object.__setattr__
        sf(self, 'category', category)
        sf(self, 'package', pkgname)
        sf(self, 'ver', ver)
        sf(self, 'rev', rev)

    @property
    def fullver(self):
        if self.rev is None:
            return self.ver
        else:
            return self.ver + "-" + self.rev

    @property
    def cp_str(self):
        return self.category + "/" + self.package

    @property
    def cpv_str(self):
        return self.cp_str + "-" + self.fullver

    def __hash__(self):
        return hash(self._all_attrs())

    def __repr__(self):
        return '<%s key=%s @%#8x>' % (self.__class__.__name__, self.cpv_str, id(self))

    def __str__(self):
        return self.cpv_str

    def __eq__(self, other):
        return isinstance(other, CPV) and self._all_attrs() == other._all_attrs()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if not isinstance(other, CPV):
            raise TypeError(f"'<' not supported between instances of {self.__class__.__name__!r} and {other.__class__.__name__!r}")
        if self._cp_attrs() != other._cp_attrs():
            raise TypeError(f"'<' not supported between {self.cpv_str!r} and {other.cpv_str!r}")
        return package_fullver_cmp(self.version, self.revision, other.version, other.revision) < 0

    def __le__(self, other):
        if not isinstance(other, CPV):
            raise TypeError(f"'<=' not supported between instances of {self.__class__.__name__!r} and {other.__class__.__name__!r}")
        if self._cp_attrs() != other._cp_attrs():
            raise TypeError(f"'<=' not supported between {self.cpv_str!r} and {other.cpv_str!r}")
        return package_fullver_cmp(self.version, self.revision, other.version, other.revision) <= 0

    def __gt__(self, other):
        if not isinstance(other, CPV):
            raise TypeError(f"'>' not supported between instances of {self.__class__.__name__!r} and {other.__class__.__name__!r}")
        if self._cp_attrs() != other._cp_attrs():
            raise TypeError(f"'>' not supported between {self.cpv_str!r} and {other.cpv_str!r}")
        return package_fullver_cmp(self.version, self.revision, other.version, other.revision) > 0

    def __ge__(self, other):
        if not isinstance(other, CPV):
            raise TypeError(f"'>=' not supported between instances of {self.__class__.__name__!r} and {other.__class__.__name__!r}")
        if self._cp_attrs() != other._cp_attrs():
            raise TypeError(f"'>=' not supported between {self.cpv_str!r} and {other.cpv_str!r}")
        return package_fullver_cmp(self.version, self.revision, other.version, other.revision) >= 0

    def _cp_attrs(self):
        return (self.category, self.package)

    def _all_attrs(self):
        return (self.category, self.package, self.ver, self.rev)


class InvalidCPV(ValueError):
    """CPV with unsupported characters or format."""

    def __init__(self, cpv_str, err=None):
        self.atom = cpv_str
        self.err = err
        super().__init__(str(self))

    def __str__(self):
        msg = f'invalid CPV: {self.cpv_str!r}'
        if self.err is not None:
            msg += f': {self.err}'
        return msg


def package_fullver_cmp(ver1, rev1, ver2, rev2):
    def cmp(a, b):
        return a > b

    # If the versions are the same, comparing revisions will suffice.
    if ver1 == ver2:
        return package_revision_cmp(rev1, rev2)

    # Split up the versions into dotted strings and lists of suffixes.
    parts1 = ver1.split("_")
    parts2 = ver2.split("_")

    # If the dotted strings are equal, we can skip doing a detailed comparison.
    if parts1[0] != parts2[0]:

        # First split up the dotted strings into their components.
        ver_parts1 = parts1[0].split(".")
        ver_parts2 = parts2[0].split(".")

        # Pull out any letter suffix on the final components and keep
        # them for later.
        letters = []
        for ver_parts in (ver_parts1, ver_parts2):
            if ver_parts[-1][-1].isalpha():
                letters.append(ord(ver_parts[-1][-1]))
                ver_parts[-1] = ver_parts[-1][:-1]
            else:
                # Using -1 simplifies comparisons later
                letters.append(-1)

        # OPT: Pull length calculation out of the loop
        ver_parts1_len = len(ver_parts1)
        ver_parts2_len = len(ver_parts2)

        # Iterate through the components
        for v1, v2 in zip(ver_parts1, ver_parts2):

            # If the string components are equal, the numerical
            # components will be equal too.
            if v1 == v2:
                continue

            # If one of the components begins with a "0" then they
            # are compared as floats so that 1.1 > 1.02; else ints.
            if v1[0] != "0" and v2[0] != "0":
                v1 = int(v1)
                v2 = int(v2)
            else:
                # handle the 0.060 == 0.060 case.
                v1 = v1.rstrip("0")
                v2 = v2.rstrip("0")

            # If they are not equal, the higher value wins.
            c = cmp(v1, v2)
            if c:
                return c

        if ver_parts1_len > ver_parts2_len:
            return 1
        elif ver_parts2_len > ver_parts1_len:
            return -1

        # The dotted components were equal. Let's compare any single
        # letter suffixes.
        if letters[0] != letters[1]:
            return cmp(letters[0], letters[1])

    # The dotted components were equal, so remove them from our lists
    # leaving only suffixes.
    del parts1[0]
    del parts2[0]

    # OPT: Pull length calculation out of the loop
    parts1_len = len(parts1)
    parts2_len = len(parts2)

    # Iterate through the suffixes
    for x in range(max(parts1_len, parts2_len)):

        # If we're at the end of one of our lists, we need to use
        # the next suffix from the other list to decide who wins.
        if x == parts1_len:
            match = _suffix_regexp.match(parts2[x])
            val = _suffix_value[match.group(1)]
            if val:
                return cmp(0, val)
            return cmp(0, int("0"+match.group(2)))
        if x == parts2_len:
            match = _suffix_regexp.match(parts1[x])
            val = _suffix_value[match.group(1)]
            if val:
                return cmp(val, 0)
            return cmp(int("0"+match.group(2)), 0)

        # If the string values are equal, no need to parse them.
        # Continue on to the next.
        if parts1[x] == parts2[x]:
            continue

        # Match against our regular expression to make a split between
        # "beta" and "1" in "beta1"
        match1 = _suffix_regexp.match(parts1[x])
        match2 = _suffix_regexp.match(parts2[x])

        # If our int'ified suffix names are different, use that as the basis
        # for comparison.
        c = cmp(_suffix_value[match1.group(1)], _suffix_value[match2.group(1)])
        if c:
            return c

        # Otherwise use the digit as the basis for comparison.
        c = cmp(int("0"+match1.group(2)), int("0"+match2.group(2)))
        if c:
            return c

    # Our versions had different strings but ended up being equal.
    # The revision holds the final difference.
    return package_revision_cmp(rev1, rev2)


def package_revision_cmp(rev1, rev2):
    rev1 = int(rev1[1:]) if rev1 is not None else 0
    rev2 = int(rev2[1:]) if rev2 is not None else 0
    return cmp(rev1, rev2)


_package_version_re = re.compile(r"^(?:\d+)(?:\.\d+)*[a-zA-Z]?(?:_(p(?:re)?|beta|alpha|rc)\d*)*$")     # FIXME: change to lazy+compile + weak-ref? test performance first

_suffix_regexp = re.compile('^(alpha|beta|rc|pre|p)(\\d*)$')
_suffix_value = {"pre": -2, "p": 1, "alpha": -4, "beta": -3, "rc": -1}
