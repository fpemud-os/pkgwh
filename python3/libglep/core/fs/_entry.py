"""
filesystem entry abstractions
"""

import fnmatch
import stat
from os.path import abspath, basename, dirname, realpath
from os.path import sep as path_seperator

from snakeoil import klass
from snakeoil.chksum import get_chksums, get_handlers
from snakeoil.compatibility import cmp
from snakeoil.currying import post_curry, pretty_docs
from snakeoil.data_source import local_source
from snakeoil.mappings import LazyFullValLoadDict
from snakeoil.osutils import normpath, pjoin

# goofy set of classes representating the fs objects pkgcore knows of.

__all__ = [
    "FileEntry", "DirEntry", "fsSymlink", "FifoEntry"]
__all__.extend(
    f"is{x}" for x in ("dir", "reg", "sym", "fifo", "dev", "fs_obj"))

# following are used to generate appropriate __init__, wiped from the
# namespace at the end of the module

_fs_doc = {
    "mode":""":keyword mode: int, the mode of this entry.  """
        """required if strict is set""",
    "mtime":""":keyword mtime: long, the mtime of this entry.  """
        """required if strict is set""",
    "uid":""":keyword uid: int, the uid of this entry.  """
        """required if strict is set""",
    "gid":""":keyword gid: int, the gid of this entry.  """
        """required if strict is set""",
}

def gen_doc_additions(init, slots):
    if init.__doc__ is None:
        d = \
"""
:param location: location (real or intended) for this entry
:param strict: is this fully representative of the entry, or only partially
:raise KeyError: if strict is enabled, and not all args are passed in
""".split("\n")
    else:
        d = init.__doc__.split("\n")
    init.__doc__ = "\n".join(k.lstrip() for k in d) + \
        "\n".join(_fs_doc[k] for k in _fs_doc if k in slots)


class Entry:
    """base class, all extensions must derive from this class"""

    __slots__ = ("location", "mtime", "mode", "uid", "gid")
    __attrs__ = __slots__
    __default_attrs__ = {}

    klass.inject_richcmp_methods_from_cmp(locals())
    klass.inject_immutable_instance(locals())

    def __init__(self, location, strict=True, **d):

        d["location"] = normpath(location)

        s = object.__setattr__
        if strict:
            for k in self.__attrs__:
                s(self, k, d[k])
        else:
            for k, v in d.items():
                s(self, k, v)
    gen_doc_additions(__init__, __attrs__)

    def change_attributes(self, **kwds):
        d = {x: getattr(self, x)
             for x in self.__attrs__ if hasattr(self, x)}
        d.update(kwds)
        # split location out
        location = d.pop("location")
        if not location.startswith(path_seperator):
            location = abspath(location)
        d["strict"] = False
        return self.__class__(location, **d)

    def __getattr__(self, attr):
        # we would only get called if it doesn't exist.
        if attr not in self.__attrs__:
            raise AttributeError(self, attr)
        obj = self.__default_attrs__.get(attr)
        if not callable(obj):
            return obj
        return obj(self)

    def __hash__(self):
        return hash(self.location)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.location == other.location

    def __ne__(self, other):
        return not self == other

    def realpath(self, cache=None):
        """calculate the abspath/canonicalized path for this entry, returning
        a new instance if the path differs.

        :keyword cache: Either None (no cache), or a data object of path->
          resolved.  Currently unused, but left in for forwards compatibility
        """
        new_path = realpath(self.location)
        if new_path == self.location:
            return self
        return self.change_attributes(location=new_path)

    @property
    def basename(self):
        return basename(self.location)

    @property
    def dirname(self):
        return dirname(self.location)

    def fnmatch(self, pattern):
        return fnmatch.fnmatch(self.location, pattern)

    def __cmp__(self, other):
        return cmp(self.location, other.location)

    def __str__(self):
        return self.location


class _LazyChksums(LazyFullValLoadDict):
    __slots__ = ()


class FileEntry(Entry):

    """file class"""

    __slots__ = ("chksums", "data", "dev", "inode")
    __attrs__ = Entry.__attrs__ + __slots__
    __default_attrs__ = {"mtime":0, 'dev':None, 'inode':None}

    def __init__(self, location, chksums=None, data=None, **kwds):
        """
        :param chksums: dict of checksums, key chksum_type: val hash val.
            See :obj:`snakeoil.chksum`.
        """
        assert 'data_source' not in kwds
        if data is None:
            data = local_source(location)
        kwds["data"] = data

        if chksums is None:
            # this can be problematic offhand if the file is modified
            # but chksum not triggered
            chf_types = kwds.pop("chf_types", None)
            if chf_types is None:
                chf_types = tuple(get_handlers())
            chksums = _LazyChksums(chf_types, self._chksum_callback)
        kwds["chksums"] = chksums
        Entry.__init__(self, location, **kwds)
    gen_doc_additions(__init__, __slots__)

    def __repr__(self):
        return f"file:{self.location}"

    data_source = klass.alias_attr("data")

    def _chksum_callback(self, chfs):
        return list(zip(chfs, get_chksums(self.data, *chfs)))

    def change_attributes(self, **kwds):
        if 'data' in kwds and ('chksums' not in kwds and
            isinstance(self.chksums, _LazyChksums)):
            kwds['chksums'] = None
        return Entry.change_attributes(self, **kwds)

    def _can_be_hardlinked(self, other):
        if not isinstance(other, FileEntry):
            return False

        if None in (self.inode, self.dev):
            return False

        for attr in ('dev', 'inode', 'uid', 'gid', 'mode', 'mtime'):
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True


class DirEntry(Entry):

    """dir class"""

    __slots__ = ()

    def __repr__(self):
        return f"dir:{self.location}"


class SymlinkEntry(Entry):

    """symlink class"""

    __slots__ = ("target",)
    __attrs__ = Entry.__attrs__ + __slots__

    def __init__(self, location, target, **kwargs):
        """
        :param target: string, filepath of the symlinks target
        """
        kwargs["target"] = target
        Entry.__init__(self, location, **kwargs)
    gen_doc_additions(__init__, __slots__)

    def change_attributes(self, **kwds):
        d = {x: getattr(self, x)
             for x in self.__attrs__ if hasattr(self, x)}
        d.update(kwds)
        # split location out
        location = d.pop("location")
        if not location.startswith(path_seperator):
            location = abspath(location)
        target = d.pop("target")
        d["strict"] = False
        return self.__class__(location, target, **d)

    @property
    def resolved_target(self):
        if self.target.startswith("/"):
            return self.target
        return normpath(pjoin(self.location, '../', self.target))

    def __cmp__(self, other):
        c = cmp(self.location, other.location)
        if c:
            return c
        if isinstance(other, self.__class__):
            return cmp(self.target, other.target)
        return 0

    def __str__(self):
        return f'{self.location} -> {self.target}'

    def __repr__(self):
        return f"symlink:{self.location}->{self.target}"


class FifoEntry(Entry):

    """fifo class (socket objects)"""

    __slots__ = ()

    def __repr__(self):
        return f"fifo:{self.location}"


del gen_doc_additions
