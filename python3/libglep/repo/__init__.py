import sys
import snakeoil
from snakeoil import klass
from snakeoil.osutils import access, listdir_dirs, listdir_files, pjoin
from snakeoil.bash import iter_read_bash, readfile, readlines

from python3.libglep.errors import ProfileParseError
from python3.libglep.repo.profiles import KnownProfile
from ._pkg_updates import pkg_updates

import os
import glob
from snakeoil import klass
from snakeoil.bash import read_dict
from snakeoil.data_source import local_source
from snakeoil.osutils import access, listdir_dirs, listdir_files, pjoin
from snakeoil.mappings import ImmutableDict
from .metadata import LayoutConf
from ... import CP, CPV


class Repo:
    """Raw implementation supporting standard ebuild tree.

    Return packages don't have USE configuration bound to them.
    """

    def __init__(self, location):
        """
        :param location: on disk location of the tree
        """
        sf = object.__setattr__

        sf(self, "location", location)

        fobj = LayoutConf(self._metadata_path("layout.conf"))
        sf(self, 'repo_name', fobj.repo_name)
        sf(self, 'manifests', fobj.manifests)
        sf(self, 'masters', fobj.masters)
        sf(self, 'aliases', fobj.aliases)
        sf(self, 'properties_allowed', fobj.properties_allowed)
        sf(self, 'restrict_allowed', fobj.restrict_allowed)
        sf(self, 'eapis_banned', fobj.eapis_banned)
        sf(self, 'eapis_deprecated', fobj.eapis_deprecated)
        sf(self, 'sign_commits', fobj.sign_commits)
        sf(self, 'cache_format', fobj.cache_format)
        sf(self, 'profile_formats', fobj.profile_formats)

    @klass.jit_attr
    def thirdpartymirrors(self):                                        # FIXME: is it a property? (aka what jit_attr does?)
        mirrors = {}
        try:
            fp = self._profile_path('thirdpartymirrors')
            for k, v in read_dict(fp, splitter=None).items():
                v = v.split()
                mirrors[k] = v
        except FileNotFoundError:
            pass
        return ImmutableDict(mirrors)

    @klass.jit_attr
    def arches(self):
        """All valid KEYWORDS for the repo."""
        try:
            return frozenset(iter_read_bash(self._profile_path('arch.list')))
        except FileNotFoundError:
            return frozenset()

    @klass.jit_attr
    def arches_desc(self):
        """Arch stability status (GLEP 72).

        See https://www.gentoo.org/glep/glep-0072.html for more details.
        """
        fp = self._profile_path('arches.desc')
        d = {'stable': set(), 'transitional': set(), 'testing': set()}
        try:
            for lineno, line in iter_read_bash(fp, enum_line=True):
                try:
                    arch, status = line.split()
                except ValueError:
                    raise ParseError(f"{fp} line {lineno}: invalid line format: should be '<arch> <status>'")
                if arch not in self.arches:
                    raise ParseError(f"{fp} line {lineno}: unknown arch: {arch!r}")
                if status not in d:
                    raise ParseError(f"{fp} line {lineno}: unknown status: {status!r}")
                d[status].add(arch)
        except FileNotFoundError:
            pass
        return snakeoil.mappings.ImmutableDict(d)

    @klass.jit_attr
    def use_desc(self):
        """Global USE flags for the repo."""
        d = self._split_use_desc_file(self._profile_path('use.desc'))
        return snakeoil.mappings.ImmutableDict(d)

    @klass.jit_attr
    def use_local_desc(self):
        """Local USE flags for the repo."""
        d = self._split_use_desc_file(self._profile_path('use.local.desc'))
        return snakeoil.mappings.ImmutableDict(d)

    @klass.jit_attr
    def use_expand_desc(self):
        """USE_EXPAND settings for the repo."""

        try:
            targets = listdir_files(self._profile_path("desc"))
        except FileNotFoundError:
            targets = []

        d = {}
        for use_group in targets:
            group = use_group.split('.', 1)[0]      # remove file extension
            d[group] = self._split_use_desc_file(self._profile_path("desc", use_group), lambda k: f'{group}_{k}')
            d[group] = snakeoil.mappings.ImmutableDict(d[group])

        return snakeoil.mappings.ImmutableDict(d)

    @klass.jit_attr
    def pms_repo_name(self):
        """Repository name from profiles/repo_name (as defined by PMS).

        We're more lenient than the spec and don't verify it conforms to the specified format.
        """
        name = readfile(self._profile_path('repo_name'), none_on_missing=True)
        if name is not None:
            name = name.split('\n', 1)[0].strip()
        return name

    @klass.jit_attr
    def updates(self):
        """Package updates for the repo defined in profiles/updates/*."""
        d = pkg_updates.read_updates(self._profile_path('updates'), self.eapi)
        return snakeoil.mappings.ImmutableDict(d)

    @klass.jit_attr
    def categories(self):
        """Contents from profiles/categories"""
        categories = readlines(self._profile_path('categories'), True, True, True)
        if categories is not None:
            return tuple(map(sys.intern, categories))
        return ()

    @klass.jit_attr
    def known_profiles(self):
        """Return the mapping of arches to profiles and profile status for a repo, according to 'profiles/profiles.desc'
        and 'deprecated' flag file in profile directory."""
        l = {}
        try:
            fp = self._fullpath('profiles.desc')
            for lineno, line in iter_read_bash(fp, enum_line=True):
                try:
                    arch, profile, status = line.split()
                except ValueError:
                    raise ParseError(f"{fp} line {lineno}: invalid profile line format: should be 'arch profile status'")

                if status not in _known_status:
                    raise ParseError(f"{fp} line {lineno}: unknown profile status: {status!r}")
                if arch not in self.arches:
                    raise ParseError(f"{fp} line {lineno}: unknown arch: {arch!r}")

                if arch not in l:
                    l[arch] = {}

                # Normalize the profile name on the offchance someone slipped an extra / into it.
                path = '/'.join(filter(None, profile.split('/')))
                deprecated = os.path.exists(self._fullpath(path, 'deprecated'))
                l[arch][profile] = KnownProfile(arch, profile, status, deprecated)
        except FileNotFoundError:
            # no profiles exist
            pass
        return l                                                        # FIXME: make it read-only

    def query_CPs(self, category=None):                                 # FIXME: should have more advanced query parameter
        if category is None:
            ret = []
            for c in self.get_categories():
                cpath = pjoin(self.location, category)
                ret += [CP(category, x, _do_check=False) for x in listdir_dirs(cpath)]
            return ret
        else:
            assert category in self.get_categories
            cpath = pjoin(self.location, category)
            return [CP(category, x) for x in listdir_dirs(cpath)]

    def query_CPVs(self, cp_obj=None):                                  # FIXME: should have more advanced query parameter
        cpv_pattern = pjoin(self.location, cp_obj.category, cp_obj.package, f"*.{self.extension}")
        ret = glob.glob(cpv_pattern)                                                            # list all ebuild files
        assert all(x.startswith(cp_obj.package) for x in ret)
        ret = [x[len(cp_obj.package):len(self.extension)*-1] for x in ret]
        return tuple([CPV(cp_obj.category, cp_obj.package, x, _do_check=False) for x in ret])       # FIXME: why convert to tuple? for performance? for read-only?

    def get_package_dirpath(self, cp_obj):
        return pjoin(self.location, cp_obj.category, cp_obj.package)

    def get_ebuild_filename(self, cpv_obj):
        return f"{cpv_obj.package}-{cpv_obj.fullver}.{self.extension}"

    def get_ebuild_filepath(self, cpv_obj):
        return pjoin(self.location, cpv_obj.category, cpv_obj.package, self._get_ebuild_filename(cpv_obj))

    def get_ebuild_src(self, pkg):
        return local_source(self._get_ebuild_filepath(pkg), encoding='utf8')

    def __str__(self):
        return f"repo at {self.location}"

    def __repr__(self):
        return "<%s location=%r @%#8x>" % (self.__class__.__name__, self.location, id(self))

    def _profile_path(self, *args):
        # it worth noting that repository config files and profile files are both reside in 'profiles' directory
        return pjoin(self.location, "profiles", *args)

    def _metadata_path(self, *args):
        return pjoin(self.location, "metdata", *args)

    def _split_use_desc_file(self, fp, converter=None):
        try:
            line = None
            for line in iter_read_bash(fp):
                try:
                    key, val = line.split(None, 1)
                    key = converter(key)
                    yield key, val.split('-', 1)[1].strip()
                except ValueError as e:
                    raise ParseError(f'failed parsing {fp}, line {line}: {e}')
        except FileNotFoundError:
            pass
        except ValueError as e:
            raise ParseError(f'failed parsing {fp!r}: {e}')

_known_status = (KnownProfile.STATUS_STABLE, KnownProfile.STATUS_EXPERIMENTAL, KnownProfile.STATUS_DEVELOPING)
