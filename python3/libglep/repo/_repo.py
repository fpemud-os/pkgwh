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


def property_file_get_path(prefix, *paths):
    """Decorator simplifying parsing repository property files.

    :param paths: Filename components of the file to parse within that repository.
        Returns None if property file does not exist.

    This decorator pass the following parameter to the decorated function:
      property_filename, property_filepath
    So that it can be used with __raiseRepoPropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            property_filename, property_filepath = _two_path(self, prefix, *paths)
            if not os.path.exists(property_filepath):
                property_filepath = None
            return func(self, property_filename, property_filepath)
        return wrapper
    return decorator


def property_file_read(prefix, *paths):
    """Decorator simplifying parsing repository property files.

    :param paths: Filename components of the file to parse within that repository.
        Returns None if property file does not exist.

    This decorator pass the following parameter to the decorated function:
      property_filename, data
    So that it can be used with __raiseRepoPropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            property_filename, fp = _two_path(self, prefix, *paths)
            data = pathlib.Path(fp).read_text() if os.path.exists(fp) else None
            return func(self, property_filename, data)
        return wrapper
    return decorator


def property_file_read_lines(prefix, *paths, enum_line=False):
    """Decorator simplifying parsing repository property files.

    :param paths: Filename components of the file to parse within that repository.
        Returns () if property file does not exist.

    This decorator pass the following parameter to the decorated function:
      property_filename, lines
    So that it can be used with __raiseRepoPropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            property_filename, fp = _two_path(self, prefix, *paths)
            lines = iter_read_bash(fp, enum_line=enum_line) if os.path.exists(fp) else ()
            return func(self, property_filename, lines)
        return wrapper
    return decorator


def property_file_parse(prefix, *paths):
    """Decorator simplifying parsing repository property files.

    :param paths: Filename components of the file to parse within that repository.
        Nothing would be yield if property file does not exist.

    This decorator pass the following parameter to the decorated function:
      property_filename, lineno, line
    So that it can be used with __raiseRepoPropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            property_filename, fp = _two_path(self, prefix, *paths)
            lines = iter_read_bash(fp, enum_line=True) if os.path.exists(fp) else ()
            for lineno, line in lines:
                yield func(self, property_filename, lineno, line)
        return wrapper
    return decorator


class Repo:
    """Raw implementation supporting standard ebuild tree."""

    def __init__(self, location):
        """
        :param location: on disk location of the tree
        """
        sf = object.__setattr__

        sf(self, "location", location)

        fobj = LayoutConf(_two_path(self, "metadata", "layout.conf")[1])
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

    def __str__(self):
        return f"repo at {self.location}"

    def __repr__(self):
        return "<%s location=%r @%#8x>" % (self.__class__.__name__, self.location, id(self))

    @klass.jit_attr
    def thirdpartymirrors(self):
        mirrors = {}
        try:
            fp = _two_path(self, "profiles", 'thirdpartymirrors')[1]
            for k, v in read_dict(fp, splitter=None).items():
                v = v.split()
                mirrors[k] = v
        except FileNotFoundError:
            pass
        return ImmutableDict(mirrors)

    @klass.jit_attr
    @property_file_read_lines("profiles", "arch.list")
    def arches(self, property_filename, lines):
        """All valid KEYWORDS for the repo."""
        return frozenset(lines)

    @klass.jit_attr
    @property_file_read_lines("profiles", "arches.desc", enum_line=True)
    def arches_desc(self, property_filename, lines):
        """Arch stability status (GLEP 72).

        See https://www.gentoo.org/glep/glep-0072.html for more details.
        """
        d = {'stable': set(), 'transitional': set(), 'testing': set()}
        for lineno, line in lines:
            try:
                arch, status = line.split()
            except ValueError:
                self.__raiseRepoPropertyFileParseError("invalid line format: should be '<arch> <status>'")
            if arch not in self.arches:
                self.__raiseRepoPropertyFileParseError(f"unknown arch: {arch!r}")
            if status not in d:
                self.__raiseRepoPropertyFileParseError(f"unknown status: {status!r}")
            d[status].add(arch)
        return ImmutableDict(d)

    @klass.jit_attr
    @property_file_get_path("profiles", "use.desc")
    def use_desc(self, property_filename, property_filepath):
        """Global USE flags for the repo."""
        d = self._split_use_desc_file(property_filename, property_filepath)
        return ImmutableDict(d)

    @klass.jit_attr
    @property_file_get_path("profiles", "use.local.desc")
    def use_local_desc(self, property_filename, property_filepath):
        """Local USE flags for the repo."""
        d = self._split_use_desc_file(property_filename, property_filepath)
        return ImmutableDict(d)

    @klass.jit_attr
    def use_expand_desc(self):
        """USE_EXPAND settings for the repo."""

        try:
            targets = listdir_files(_two_path(self, "profiles", "desc")[1])
        except FileNotFoundError:
            targets = []

        d = {}
        for use_group in targets:
            group = use_group.split('.', 1)[0]      # remove file extension
            property_filename, property_filepath = _two_path(self, "profiles", "desc", use_group)
            d[group] = self._split_use_desc_file(property_filename, property_filepath, lambda k: f'{group}_{k}')
            d[group] = ImmutableDict(d[group])

        return ImmutableDict(d)

    @klass.jit_attr
    @property_file_read("profiles", "repo_name")
    def pms_repo_name(self, property_filename, data):
        """Repository name from profiles/repo_name (as defined by PMS).

        We're more lenient than the spec and don't verify it conforms to the specified format.
        """
        if data is not None:
            return data.split('\n', 1)[0].strip()
        else:
            return None

    @klass.jit_attr
    def updates(self):
        """Package updates for the repo defined in profiles/updates/*."""
        d = pkg_updates.read_updates(_two_path(self, "profiles", 'updates')[1], self.eapi)
        return ImmutableDict(d)

    @klass.jit_attr
    def categories(self):
        """Contents from profiles/categories"""
        categories = readlines(_two_path(self, "profiles", 'categories')[1], True, True, True)
        if categories is not None:
            return tuple(map(sys.intern, categories))
        return ()

    @klass.jit_attr
    @property_file_read_lines("profiles", "profiles.desc", enum_line=True)
    def known_profiles(self, property_filename, lines):
        """Return the mapping of arches to profiles and profile status for a repo, according to 'profiles/profiles.desc'
        and 'deprecated' flag file in profile directory."""
        l = {}
        for lineno, line in lines:
            try:
                arch, profile, status = line.split()
            except ValueError:
                self.__raiseRepoPropertyFileParseError("invalid profile line format: should be 'arch profile status'")
            if status not in _known_status:
                self.__raiseRepoPropertyFileParseError(f"unknown profile status: {status!r}")
            if arch not in self.arches:
                self.__raiseRepoPropertyFileParseError(f"unknown arch: {arch!r}")
            if None in profile.split('/'):
                self.__raiseRepoPropertyFileParseError(f"extra / found: {profile!r}")   # someone has slipped extra / into profile name

            deprecated = os.path.exists(_two_path(self, "profiles", profile, 'deprecated')[1])

            if arch not in l:
                l[arch] = {}
            l[arch][profile] = KnownProfile(arch, profile, status, deprecated)
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

    def _split_use_desc_file(self, property_filename, property_filepath, converter=None):
        if property_filepath is not None:
            for lineno, line in iter_read_bash(property_filepath, enum_line=True):
                try:
                    key, val = line.split(None, 1)
                    key = converter(key)
                    yield key, val.split('-', 1)[1].strip()
                except ValueError as e:
                    self.__raiseRepoPropertyFileParseError(f"{e}")

    def __raiseRepoPropertyFileParseError(self, error_str):
        # this function reads the following variables in caller function:
        #   property_filename, line, lineno
        f_locals = inspect.stack()[0].f_locals
        raise RepoPropertyFileParseError(self,
                                         f_locals["property_filename"],
                                         error_str,
                                         f_locals.get("lineno"),
                                         f_locals.get("line"))


class RepoError(Exception):
    pass


class RepoPropertyFileParseError(RepoError):
    """Repository property file parse failed."""

    def __init__(self, repo, property_filename, error, lineno=None, line=None):
        # no performance concern is needed for exception object

        assert isinstance(repo, Repo)
        assert isinstance(property_filename, str) and "/" not in property_filename
        assert isinstance(error, str)
        if lineno is not None:
            assert isinstance(lineno, int)
            assert isinstance(line, str)
        else:
            assert line is None

        self._repo = repo
        self._filename = property_filename
        self._error = error
        self._lineno = lineno
        self._line = line

    def __str__(self):
        ret = "failed parsing %s in %s: %s" % (self._filename, self._repo, self._error)
        if line is not None:
            ret += ", line %d: %s" % (self._lineno, self._line)
        return ret


def _two_path(repo, prefix, *paths):
    # it worth noting that repository config files and profile files are both reside in 'profiles' directory
    assert prefix in ["metadata", "profiles"]
    fn = pjoin(prefix, *paths)
    fullfn = pjoin(repo.location, fn)
    return (fn, fullfn)


_known_status = (KnownProfile.STATUS_STABLE, KnownProfile.STATUS_EXPERIMENTAL, KnownProfile.STATUS_DEVELOPING)
