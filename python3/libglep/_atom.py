#!/usr/bin/env python3

import re
import string
from snakeoil import klass
from ... import errors
from ._cpv import is_valid_category, is_valid_package_name, is_valid_package_version, is_valid_package_revision, CP, CPV


def is_valid_prefix_op(s):
    assert isinstance(s, str)
    return (s in _valid_ops)


def is_valid_repository(s):
    assert isinstance(s, str)
    if len(s) == 0:
        return False
    if s[0] == "-":
        return False
    if not _valid_repo_chars.issuperset(s):
        return False
    return True


def is_valid_slot(s):
    assert isinstance(s, str) and len(s) > 0
    if s[0] in ("-", "."):
        return False
    if not _valid_slot_chars.issuperset(s):
        return False
    return True


def is_valid_subslot(s):
    return is_valid_slot(s)                 # same as slot


def is_valid_use_flag(s):
    assert isinstance(s, str)
    return _valid_use_flag_re.fullmatch(s)


class PkgAtom(klass.SlotsPicklingMixin, metaclass=klass.immutable_instance):
    """Currently implements gentoo ebuild atom parsing.

    :ivar blocks: bool has ! operator
    :ivar blocks_strongly: bool has !! operator
    :ivar op: str prefix operator, optional
    :ivar category: str category name, may contain wildcard
    :ivar package: str package name, may contain wildcard
    :ivar slot: str slot, optional
    :ivar slot_operator: str slot operator, optional
    :ivar subslot: str subslot, optional
    :ivar ver: str version, optional, may contain wildcard
    :ivar rev: str revision, optional, may contain wildcard
    :ivar fullver: str version-revision
    :ivar post_wildcard: bool has * postfix
    :ivar use: list USE flags, optional
    :ivar repo_id: str repository name, optional
    :ivar key: str (category/package-version-revision)
    """

    def __init__(self, atom, eapi=None):
        """
        :param atom: string, see gentoo ebuild atom syntax
        :keyword eapi: int controlling what eapi to enforce for this atom
        """

        if eapi is not None:
            assert eapi >= 0
            if eapi <= 4:
                raise ValueError("EAPI={eapi!r} is not supported")

        sf = object.__setattr__
        orig_atom = atom

        # self.use
        use_start = atom.find("[")
        if use_start != -1:
            # use dep
            use_end = atom.find("]", use_start)
            if use_end == -1:
                raise errors.InvalidAtom(orig_atom, "use restriction isn't completed")
            elif use_end != len(atom) - 1:
                raise TypeError("trailing garbage in atom arg after use dep")
            sf(self, "use", tuple(sorted(atom[use_start + 1:use_end].split(','))))
            for x in self.use:
                # stripped purely for validation reasons
                try:
                    if x[-1] in "=?":
                        override_kls = True
                        x = x[:-1]
                        if x[0] == '!':
                            x = x[1:]
                        if x[0] == '-':
                            raise errors.InvalidAtom(orig_atom, f"malformed use flag: {x}")
                    elif x[0] == '-':
                        x = x[1:]

                    if x[-1] == ')':
                        # use defaults.
                        if x[-3:] in ("(+)", "(-)"):
                            x = x[:-3]

                    if not x:
                        raise errors.InvalidAtom(orig_atom, 'empty use dep detected')
                    if not is_valid_use_flag(x):
                        raise errors.InvalidAtom(orig_atom, f'invalid USE flag: {x!r}')
                except IndexError:
                    raise errors.InvalidAtom(orig_atom, 'empty use dep detected')
            atom = atom[:use_start] + atom[use_end + 1:]
        else:
            sf(self, "use", None)

        # self.repo_id
        repo_id_start = atom.find("::")
        if repo_id_start != -1:
            repo_id = atom[repo_id_start+2:]
            if repo_id == "":
                raise errors.InvalidAtom(orig_atom, "repo_id must not be empty")
            if not is_valid_repository(repo_id):
                raise errors.InvalidAtom(orig_atom, f"invalid repo_id component: {repo_id!r}")
            atom = atom[:repo_id_start]
            sf(self, "repo_id", repo_id)
        else:
            sf(self, "repo_id", None)

        # self.slot, self.slot_operator, self.subslot
        slot_start = atom.find(":")
        if slot_start != -1:
            # slot dep.
            slot = atom[slot_start+1:]
            if slot == "":
                raise errors.InvalidAtom(orig_atom, "empty slot targets aren't allowed")        # FIXME: targets->target?

            if slot[0] in ("*", "="):
                if len(slot) > 1:
                    raise errors.InvalidAtom(orig_atom, "slot operators '*' and '=' do not take slot targets")
                slot_operator = slot
                slot = None
                subslot = None
            else:
                if slot[-1] == '=':
                    slot = slot[:-1]
                    slot_operator = '='
                else:
                    slot_operator = None

                slots = slot.split('/')
                if len(slots) == 1:
                    subslot = None
                elif len(slots) == 2:
                    slot = slots[0]
                    subslot = slots[1]
                    if slot == "":
                        raise errors.InvalidAtom(orig_atom, "empty slot targets aren't allowed")
                    if subslot == "":
                        raise errors.InvalidAtom(orig_atom, "empty subslot targets aren't allowed")
                else:
                    raise errors.InvalidAtom(orig_atom, f"redundant character in slot/subslot component: {slot!r}")

                if slot is not None and not is_valid_slot(slot):
                    raise errors.InvalidAtom(orig_atom, "invalid slot targets")
                if subslot is not None and not is_valid_subslot(slot):
                    raise errors.InvalidAtom(orig_atom, "invalid subslot targets")

            sf(self, "slot", slot)
            sf(self, "slot_operator", slot_operator)
            sf(self, "subslot", subslot)
            atom = atom[:slot_start]
        else:
            sf(self, "slot", None)
            sf(self, "slot_operator", None)
            sf(self, "subslot", None)

        # self.blocks and self.blocks_strongly
        sf(self, "blocks", atom[0] == "!")
        if self.blocks:
            atom = atom[1:]
            sf(self, "blocks_strongly", atom[0] == "!")
            if self.blocks_strongly:
                atom = atom[1:]

        # self.op
        if atom[0] in ('<', '>'):
            if atom[1] == '=':
                sf(self, 'op', atom[:2])
                atom = atom[2:]
            else:
                sf(self, 'op', atom[0])
                atom = atom[1:]
        elif atom[0] == '=':
            atom = atom[1:]
            sf(self, 'op', '=')
        elif atom[0] == '~':
            sf(self, 'op', '~')
            atom = atom[1:]
        else:
            sf(self, 'op', None)

        # self.post_wildcard
        if atom[-1] == '*':
            sf(self, 'post_wildcard', True)
            atom = atom[:-1]

        # self.category, self.package, self.ver, self.rev
        if True:
            try:
                category, pkg_name_ver = atom.rsplit("/", 1)
            except ValueError:
                raise errors.InvalidAtom(orig_atom, "no category component")     # occurs if the rsplit yields only one item
            pkg_chunks = pkg_name_ver.split("-")
            pkgname = pkg_chunks[0]
            if len(pkg_chunks) == 1:
                ver = None
                rev = None
            else:
                if is_valid_package_revision(pkg_chunks[-1]):
                    ver = "-".join(pkg_chunks[1:-1])
                    rev = pkg_chunks[-1]
                else:
                    ver = pkg_chunks[1:]
                    rev = None

            if not is_valid_category(category):
                raise errors.InvalidAtom(orig_atom, "invalid category component")
            if not is_valid_package_name(pkgname):
                raise errors.InvalidAtom(orig_atom, "invalid package component")
            if not is_valid_package_version(ver):
                raise errors.InvalidAtom(orig_atom, "invalid version component")
            if rev is not None and not is_valid_package_revision(rev):
                raise errors.InvalidAtom(orig_atom, "invalid revision component")

            sf(self, 'category', category)
            sf(self, 'package', pkgname)
            sf(self, 'ver', ver)
            sf(self, 'rev', rev)

        # check for invalid combinations
        if self.op is not None:
            if self.ver is None:
                raise errors.InvalidAtom(orig_atom, "'{self.op}' operator requires a version")
            if self.op == '~' and self.revision is not None:
                raise errors.InvalidAtom(orig_atom, "'~' operator cannot be combined with a revision")
        else:
            if self.ver is not None:
                raise errors.InvalidAtom(orig_atom, 'versioned atom requires an operator')
        if self.post_wildcard and self.op != "=":
            raise errors.InvalidAtom(orig_atom, "'*' postfix requires '=' operator")

    def match(self):
        pass

    def __hash__(self):
        return hash(self._all_attrs())

    def __repr__(self):
        attrs = [self._core_str()]
        if self.use is not None:
            attrs.append(f'use={self.use!r}')
        if self.slot is not None:
            attrs.append(f'slot={self.slot!r}')
        if self.subslot is not None:
            attrs.append(f'subslot={self.subslot!r}')
        if self.repo_id is not None:
            attrs.append(f'repo_id={self.repo_id!r}')
        return '<%s %s @#%x>' % (self.__class__.__name__, ' '.join(attrs), id(self))

    def __str__(self):
        s = self._core_str()
        if self.slot is not None:
            s += f":{self.slot}"
            if self.subslot is not None:
                s += f"/{self.subslot}"
            if self.slot_operator is not None:
                s += self.slot_operator
        else:
            if self.slot_operator is not None:
                s += self.slot_operator
        if self.repo_id is not None:
            s += f"::{self.repo_id}"
        if self.use is not None:
            s += ",".join(self.use)
        return s

    def __eq__(self, other):
        try:
            return self._all_attrs() == other._all_attrs()
        except AttributeError:
            raise TypeError(f"'==' not supported between instances of {self.__class__.__name__!r} and {other.__class__.__name__!r}")

    def __ne__(self, other):
        try:
            return self._all_attrs() != other._all_attrs()
        except AttributeError:
            raise TypeError(f"'!=' not supported between instances of {self.__class__.__name__!r} and {other.__class__.__name__!r}")

    def _all_attrs(self):
        return (self.category, self.package, self.ver, self.rev, self.post_wildcard, self.op,
                self.blocks, self.blocks_strongly, self.slot, self.slot_operator, self.subslot,
                self.repo_id, self.use)

    def _core_str(self):
        s = self.category + "/" + self.package
        if self.ver is not None:
            if self.rev is None:
                s += f"-{self.ver}"
            else:
                s += f"-{self.ver}-{self.rev}"
        if self.post_wildcard:
            s += "*"
        if self.op is not None:
            s = self.op + s
        if self.blocks:
            if self.blocks_strongly:
                s = '!!' + s
            else:
                s = '!' + s
        return s




_alphanum = set(string.digits)
_alphanum.update(string.ascii_letters)

_valid_repo_chars = set(_alphanum)
_valid_repo_chars.update("_-")
_valid_repo_chars = frozenset(_valid_repo_chars)

_valid_slot_chars = set(_alphanum)
_valid_slot_chars.update(".+_-")
_valid_slot_chars = frozenset(_valid_slot_chars)

_valid_ops = frozenset(['<', '<=', '=', '~', '>=', '>'])

_valid_use_flag_re = re.compile(r'^[A-Za-z0-9][A-Za-z0-9+_@-]*$')                       # FIXME: change to lazy+compile + weak-ref, snakeoil.demandload.demand_compile_regexp() doesn't have variable form
