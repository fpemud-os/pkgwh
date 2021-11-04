"""
contents set- container of fs objects
"""

import os
import time
from collections import OrderedDict, defaultdict
from functools import partial
from operator import attrgetter

from snakeoil.klass import alias_method, generic_equality
from snakeoil.osutils import normpath, pjoin

from . import fs


def change_offset_rewriter(orig_offset, new_offset, iterable):
    path_sep = os.path.sep
    offset_len = len(orig_offset.rstrip(path_sep))
    # localize it.
    npf = normpath
    for x in iterable:
        # slip in the '/' default to force it to still generate a
        # full path still
        yield x.change_attributes(
            location=npf(pjoin(new_offset, x.location[offset_len:].lstrip(path_sep))))

offset_rewriter = partial(change_offset_rewriter, '/')


def check_instance(obj):
    if not isinstance(obj, fs.Entry):
        raise TypeError(f"'{obj}' is not a fs.Entry deriviative")
    return obj.location, obj


class ContentsSet(set):
    """set of :class:`core.fs.Entry` objects"""

    __attr_comparison__ = ('_dict',)
    __dict_kls__ = dict


    def __init__(self, initial=None):

        """
        :param initial: initial fs objs for this set
        :type initial: sequence
        :param mutable: controls if it modifiable after initialization
        """
        self._dict = self.__dict_kls__()
        if initial is not None:
            self._dict.update(check_instance(x) for x in initial)

    def __str__(self):
        name = self.__class__.__name__
        contents = ', '.join(map(str, self))
        return f'{name}([{contents}])'

    def __repr__(self):
        name = self.__class__.__name__
        contents = ', '.join(map(repr, self))
        # this should include the id among other things
        return f'{name}([{contents}])'

    def iter_files(self, invert=False):
        """A generator yielding just :obj:`pkgcore.fs.fs.fsFile` instances.

        :param invert: if True, yield everything that isn't a fsFile instance,
            else yields just fsFile instances.
        """

        if invert:
            return (x for x in self if not x.is_reg)
        return filter(attrgetter('is_reg'), self)

    def files(self, invert=False):
        """Returns a list of just :obj:`pkgcore.fs.fs.fsFile` instances.

        :param invert: if True, yield everything that isn't a
            fsFile instance, else yields just fsFile.
        """
        return list(self.iter_files(invert=invert))

    def iter_dirs(self, invert=False):
        if invert:
            return (x for x in self if not x.is_dir)
        return filter(attrgetter('is_dir'), self)

    def dirs(self, invert=False):
        return list(self.iter_dirs(invert=invert))

    def iter_symlinks(self, invert=False):
        if invert:
            return (x for x in self if not x.is_sym)
        return filter(attrgetter('is_sym'), self)

    def symlinks(self, invert=False):
        return list(self.iterlinks(invert=invert))

    def iter_fifos(self, invert=False):
        if invert:
            return (x for x in self if not x.is_fifo)
        return filter(attrgetter('is_fifo'), self)

    def fifos(self, invert=False):
        return list(self.iter_fifos(invert=invert))

    def inode_map(self):
        d = defaultdict(list)
        for obj in self.iter_files():
            key = (obj.dev, obj.inode)
            if None in key:
                continue
            d[key].append(obj)
        return d

    def insert_offset(self, offset):
        cset = self.clone(empty=True)
        cset.update(offset_rewriter(offset, self))
        return cset

    def change_offset(self, old_offset, new_offset):
        cset = self.clone(empty=True)
        cset.update(change_offset_rewriter(old_offset, new_offset, self))
        return cset

    def iter_child_nodes(self, start_point):
        """Yield a stream of nodes that are fs entries contained within the
        passed in start point.

        :param start_point: fs filepath all yielded nodes must be within.
        """

        if isinstance(start_point, fs.Entry):
            if start_point.is_sym:
                start_point = start_point.target
            else:
                start_point = start_point.location
        for x in self:
            cn_path = normpath(start_point).rstrip(os.path.sep) + os.path.sep
            # what about sym targets?
            if x.location.startswith(cn_path):
                yield x

    def child_nodes(self, start_point):
        """Return a clone of this instance, w/ just the child nodes returned
        from `iter_child_nodes`.

        :param start_point: fs filepath all yielded nodes must be within.
        """
        obj = self.clone(empty=True)
        obj.update(self.iter_child_nodes(start_point))
        return obj

    def map_directory_structure(self, other, add_conflicting_sym=True):
        """Resolve the directory structure between this instance, and another
        contentset, collapsing syms of self into directories of other.
        """
        conflicts_d = {x: x.resolved_target for x in other.iterlinks()}
        # rebuild the targets first; sorted due to the fact that we want to
        # rewrite each node (resolving down the filepath chain)
        conflicts = sorted(ContentsSet(self.iter_dirs()).intersection(conflicts_d))
        obj = self.clone()
        while conflicts:
            for conflict in conflicts:
                # punt the conflict first, since we don't want it getting rewritten
                obj.remove(conflict)
                subset = obj.child_nodes(conflict.location)
                obj.difference_update(subset)
                subset = subset.change_offset(conflict.location, conflict.resolved_target)
                obj.update(subset)
                if add_conflicting_sym:
                    obj.add(other[conflicts_d[conflict]])

            # rebuild the targets first; sorted due to the fact that we want to
            # rewrite each node (resolving down the filepath chain)
            conflicts = sorted(ContentsSet(obj.iter_dirs()).intersection(conflicts_d))
        return obj

    def add_missing_directories(self, mode=0o775, uid=0, gid=0, mtime=None):
        """Ensure that a directory node exists for each path; add if missing."""
        missing = (x.dirname for x in self)
        missing = set(x for x in missing if x not in self)
        if mtime is None:
            mtime = time.time()
        # have to go recursive since many directories may be missing.
        missing_initial = list(missing)
        for x in missing_initial:
            target = os.path.dirname(x)
            while target not in missing and target not in self:
                missing.add(target)
                target = os.path.dirname(target)
        missing.discard("/")
        self.update(fs.fsDir(location=x, mode=mode, uid=uid, gid=gid, mtime=mtime)
            for x in missing)

    @staticmethod
    def _convert_loc(iterable):
        f = fs.isfs_obj
        for x in iterable:
            if f(x):
                yield x.location
            else:
                yield x

    @staticmethod
    def _ensure_fsbase(iterable):
        f = fs.isfs_obj
        for x in iterable:
            if not f(x):
                raise ValueError(f'must be an Entry derivative: got {x!r}')
            yield x
