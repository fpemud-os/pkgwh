import os
import inspect
from snakeoil import klass
from snakeoil.osutils import abspath, pjoin
from snakeoil.bash import iter_read_bash, read_bash_dict
from snakeoil.sequences import split_negations, stable_unique
from ...core._pkg_wildcard import PkgWildcard


def property_file_get_path(property_filename, eapi_optional=None):
    """Decorator simplifying parsing profile property files.

    :param property_filename: The filename to parse within that profile directory.
        Returns None if property file does not exist.
    :keyword eapi_optional: If given, the EAPI for this profile node is checked to see if
        the given optional evaluates to True; if so, then parsing occurs.  If False, then
        None is returned and no ondisk activity occurs.

    This decorator pass the following parameter to the decorated function:
      property_filename, property_filepath
    So that it can be used with __raiseProfilePropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            property_filepath = _decorator_helper(1, self, property_filename, eapi_optional)
            return func(self, property_filename, property_filepath)
        return wrapper
    return decorator


def property_file_read(property_filename, eapi_optional=None):
    """Decorator simplifying parsing profile property files.

    :param property_filename: The filename to parse within that profile directory.
        Returns None if property file does not exist.
    :keyword eapi_optional: If given, the EAPI for this profile node is checked to see if
        the given optional evaluates to True; if so, then parsing occurs.  If False, then
        None is returned and no ondisk activity occurs.

    This decorator pass the following parameter to the decorated function:
      property_filename, data
    So that it can be used with __raiseProfilePropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            data = _decorator_helper(2, self, property_filename, eapi_optional)
            return func(self, property_filename, data)
        return wrapper
    return decorator


def property_file_read_lines(property_filename, eapi_optional=None):
    """Decorator simplifying parsing profile property files.

    :param property_filename: The filename to parse within that profile directory.
        Returns () if property file does not exist.
    :keyword eapi_optional: If given, the EAPI for this profile node is checked to see if
        the given optional evaluates to True; if so, then parsing occurs.  If False, then
        () is returned and no ondisk activity occurs.

    This decorator pass the following parameter to the decorated function:
      property_filename, lines
    So that it can be used with __raiseProfilePropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            lines = _decorator_helper(3, self, property_filename, eapi_optional)
            return func(self, property_filename, lines)
        return wrapper
    return decorator


def property_file_parse(property_filename, eapi_optional=None):
    """Decorator simplifying parsing profile property files.

    :param property_filename: The filename to parse within that profile directory.
        Nothing would be yield if property file does not exist.
    :keyword eapi_optional: If given, the EAPI for this profile node is checked to see if
        the given optional evaluates to True; if so, then parsing occurs.  If False, then
        nothing would be yeild and no ondisk activity occurs.

    This decorator pass the following parameter to the decorated function:
      property_filename, line, lineno
    So that it can be used with __raiseProfilePropertyFileParseError conveninently
    """

    def decorator(func):
        def wrapper(self):
            for line, lineno in _decorator_helper(3, self, property_filename, eapi_optional):
                yield func(self, property_filename, line, lineno)
        return wrapper
    return decorator


class Profile(metaclass=klass.immutable_instance):

    def __init__(self, repo, name, pms_strict=True):
        assert isinstance(repo, Repo)
        assert isinstance(name, str)

        # validate
        path = _profile_path(repo, name)
        if not os.path.exists(path):
            raise ProfileParseError(repo, name, path, ProfileParseError.ERR_NOT_EXIST)
        if not os.path.isdir(path):
            raise ProfileParseError(repo, name, path, ProfileParseError.ERR_INVALID)

        self._repo = repo
        self._name = name
        self._pms_strict = pms_strict

    def __str__(self):
        return "profile of %s at %s" % (self._repo, os.path.join("profiles", self._name))

    def __repr__(self):
        return '<%s repo=%r name=%r, @%#8x>' % (self.__class__.__name__, self._repo, self._name, id(self))

    def name(self):
        """Relative path to the profile from the profiles directory."""
        return self._name

    @klass.jit_attr
    @property_file_read_lines("packages")
    def packages(self, property_filename, lines):
        # TODO: get profile-set support into PMS
        profile_set = 'profile-set' in self._repo.profile_formats
        pkg_sys, pkg_neg_sys, pkg_pro, pkg_neg_pro, neg_wildcard = [], [], [], [], False
        for line, lineno in lines:
            try:
                if line[0] == '-':
                    if line == '-*':
                        neg_wildcard = True
                    elif line[1] == '*':
                        pkg_neg_sys.append(PkgWildcard(line[2:]))
                    elif profile_set:
                        pkg_neg_pro.append(PkgWildcard(line[1:]))
                    else:
                        self.__raiseProfilePropertyFileParseError("invalid line format")
                else:
                    if line[0] == '*':
                        pkg_sys.append(PkgWildcard(line[1:]))
                    elif profile_set:
                        pkg_pro.append(PkgWildcard(line))
                    else:
                        self.__raiseProfilePropertyFileParseError("invalid line format")
            except InvalidPkgWildcard as e:
                self.__raiseProfilePropertyFileParseError(f"parsing error: {e}")
        ret_system = [tuple(pkg_neg_sys), tuple(pkg_sys)]
        ret_profile = [tuple(pkg_neg_pro), tuple(pkg_pro)]
        if neg_wildcard:
            ret_system.append(neg_wildcard)
            ret_profile.append(neg_wildcard)
        return ProfilePackages(tuple(ret_system), tuple(ret_profile))

    @klass.jit_attr
    @property_file_parse("parent")
    def parent_paths(self, property_filename, line, lineno):
        if 'portage-2' in self._repo.profile_formats:
            repo_id, separator, profile_path = line.partition(':')
            if separator:
                if profile_path.find("..") >= 0:
                    self.__raiseProfilePropertyFileParseError("invalid line format")
                return (line, repo_id)

        line = abspath(pjoin(_profile_path(self._repo, self._name), line))
        if not line.startswith(self._repo.location + "/"):
            self.__raiseProfilePropertyFileParseError("profile path is not in profile directory")
        line = line[len(self._repo.location)+1:]
        return (line, None)

    @klass.jit_attr
    @property_file_parse("package.provided")
    def pkg_provided(self, property_filename, line, lineno):
        try:
            return CPV(line)
        except errors.InvalidCPV:
            self.__raiseProfilePropertyFileParseError("invalid package.provided entry")

    @klass.jit_attr
    @property_file_read_lines("package.mask")
    def masks(self, property_filename, lines):
        return self._parse_pkg_wildcard_negations(property_filename, lines)

    @klass.jit_attr
    @property_file_read_lines("package.unmask")
    def unmasks(self, property_filename, lines):
        return self._parse_pkg_wildcard_negations(property_filename, lines)

    @klass.jit_attr
    @property_file_read_lines("package.deprecated")
    def pkg_deprecated(self, property_filename, lines):
        return self._parse_pkg_wildcard_negations(property_filename, lines)

    @klass.jit_attr
    @property_file_parse("package.keywords")
    def keywords(self, property_filename, line, lineno):
        return self._package_keywords_splitter(property_filename, line, lineno)

    @klass.jit_attr
    @property_file_parse("package.accept_keywords")
    def accept_keywords(self, property_filename, line, lineno):
        return self._package_keywords_splitter(property_filename, line, lineno)

    @klass.jit_attr
    @property_file_read_lines("package.use")
    def pkg_use(self, property_filename, lines):
        c = ChunkedDataDict()
        c.update_from_stream(chain.from_iterable(self._parse_package_use(lines).values()))
        c.freeze()
        return c

    @klass.jit_attr
    @property_file_read("deprecated")
    def deprecated(self, property_filename, data):
        if data is None:
            return None     # file does not exist

        i = data.find("\n")
        if i < 0:
            self.__raiseProfilePropertyFileParseError("deprecated profile missing replacement")
        if len(data) > i + 1 and data[i+1] != "\n":
            self.__raiseProfilePropertyFileParseError("deprecated profile missing message")

        replacement = data[:i]          # replacement is in line 1
        msg = data[i+2:]                # line 2 should be empty, line 3 and the following is the message
        return (replacement, msg)

    @klass.jit_attr
    @property_file_read_lines("use.force")
    def use_force(self, property_filename, lines):
        return self._parse_use(lines)

    @klass.jit_attr
    @property_file_read_lines("use.stable.force", eapi_optional='profile_stable_use')
    def use_stable_force(self, property_filename, lines):
        return self._parse_use(lines)

    @klass.jit_attr
    @property_file_read_lines("package.use.force")
    def pkg_use_force(self, property_filename, lines):
        return self._parse_package_use(lines)

    @klass.jit_attr
    @property_file_read_lines("package.use.stable.force", eapi_optional='profile_stable_use')
    def pkg_use_stable_force(self, property_filename, lines):
        return self._parse_package_use(lines)

    @klass.jit_attr
    @property_file_read_lines("use.mask")
    def use_mask(self, property_filename, lines):
        return self._parse_use(lines)

    @klass.jit_attr
    @property_file_read_lines("use.stable.mask", eapi_optional='profile_stable_use')
    def use_stable_mask(self, property_filename, lines):
        return self._parse_use(lines)

    @klass.jit_attr
    @property_file_read_lines("package.use.mask")
    def pkg_use_mask(self, property_filename, lines):
        return self._parse_package_use(lines)

    @klass.jit_attr
    @property_file_read_lines("package.use.stable.mask", eapi_optional='profile_stable_use')
    def pkg_use_stable_mask(self, property_filename, lines):
        return self._parse_package_use(lines)

    @klass.jit_attr
    def masked_use(self):
        c = self.use_mask
        if self.pkg_use_mask:
            c = c.clone(unfreeze=True)
            c.update_from_stream(chain.from_iterable(self.pkg_use_mask.values()))
            c.freeze()
        return c

    @klass.jit_attr
    def stable_masked_use(self):
        c = self.use_mask.clone(unfreeze=True)
        if self.use_stable_mask:
            c.merge(self.use_stable_mask)
        if self.pkg_use_mask:
            c.update_from_stream(chain.from_iterable(self.pkg_use_mask.values()))
        if self.pkg_use_stable_mask:
            c.update_from_stream(chain.from_iterable(self.pkg_use_stable_mask.values()))
        c.freeze()
        return c

    @klass.jit_attr
    def forced_use(self):
        c = self.use_force
        if self.pkg_use_force:
            c = c.clone(unfreeze=True)
            c.update_from_stream(chain.from_iterable(self.pkg_use_force.values()))
            c.freeze()
        return c

    @klass.jit_attr
    def stable_forced_use(self):
        c = self.use_force.clone(unfreeze=True)
        if self.use_stable_force:
            c.merge(self.use_stable_force)
        if self.pkg_use_force:
            c.update_from_stream(chain.from_iterable(self.pkg_use_force.values()))
        if self.pkg_use_stable_force:
            c.update_from_stream(chain.from_iterable(self.pkg_use_stable_force.values()))
        c.freeze()
        return c

    @klass.jit_attr
    @property_file_read("make.defaults")
    def make_defaults(self, property_filename, data):
        if data is not None:
            return ImmutableDict(read_bash_dict(data))
        else:
            return ImmutableDict()

    @klass.jit_attr
    @property_file_read("make.defaults")
    def default_env(self, property_filename, data):
        rendered = _make_incrementals_dict()
        for parent in self.parents:
            rendered.update(parent.default_env.items())

        if data is not None:
            data = read_bash_dict(data, vars_dict=rendered)
            rendered.update(data.items())
        return ImmutableDict(rendered)

    @klass.jit_attr
    @property_file_get_path("profile.bashrc")
    def bashrc(self, property_filename, property_filepath):
        if os.path.exists(property_filepath):
            return local_source(property_filepath)
        return None

    @klass.jit_attr
    @property_file_read("eapi")
    def eapi(self, property_filename, data):
        if data is None:
            return "0"
        else:
            return data.rstrip("\n")

    def _parse_pkg_wildcard_negations(self, property_filename, iterable):
        """Parse files containing optionally negated package atoms."""
        neg, pos = [], []
        for line, lineno in iterable:
            try:
                if line[0] == '-':
                    line = line[1:]
                    if not line:
                        self.__raiseProfilePropertyFileParseError("'-' negation without an atom")
                    neg.append(PkgWildcard(line))
                else:
                    pos.append(PkgWildcard(line))
            except errors.InvalidPkgWildcard as e:
                self.__raiseProfilePropertyFileParseError("parsing error: {e}")
        return tuple(neg), tuple(pos)

    def _package_keywords_splitter(self, property_filename, line, lineno):
        """Parse package keywords files."""
        v = line.split()
        try:
            return (PkgWildcard(v[0]), tuple(stable_unique(v[1:])))
        except errors.InvalidPkgWildcard as e:
            self.__raiseProfilePropertyFileParseError("parsing error: {e}")

    def _parse_package_use(self, property_filename, iterable):
        d = defaultdict(list)

        # split the data down ordered cat/pkg lines
        for line, lineno in iterable:
            l = line.split()
            try:
                a = PkgWildcard(l[0])
            except errors.InvalidPkgWildcard as e:
                self.__raiseProfilePropertyFileParseError("parsing error: {e}")
            if len(l) == 1:
                self.__raiseProfilePropertyFileParseError("missing USE flag(s)")
            d[a.key].append(misc.chunked_data(a, *split_negations(l[1:])))

        return ImmutableDict((k, misc._build_cp_atom_payload(v, atom(k))) for k, v in d.items())

    def _parse_use(self, property_filename, data):
        c = misc.ChunkedDataDict()
        data = (x[0] for x in data)
        neg, pos = split_negations(data)
        if neg or pos:
            c.add_bare_global(neg, pos)
        c.freeze()
        return c

    def __raiseProfilePropertyFileParseError(self, error_str):
        # this function reads the following variables in caller function:
        #   property_filename, line, lineno
        f_locals = inspect.stack()[0].f_locals
        raise ProfilePropertyFileParseError(self,
                                            f_locals["property_filename"],
                                            error_str,
                                            f_locals.get("line"),
                                            f_locals.get("lineno"))


class ProfilePackages:

    def __init__(self, sys, pro):
        self.system = sys
        self.profiles = pro


class ProfileError(Exception):
    pass


class ProfileParseError(ProfileError):
    """Profile parse failed."""

    ERR_NOT_EXIST = 1       # profile for a nonexistent directory
    ERR_INVALID = 2         # profile directory not valid

    def __init__(self, repo, name, path, err):
        # no performance concern is needed for exception object

        assert isinstance(repo, Repo)
        assert isinstance(name, str)
        assert ininstance(path, str)
        assert err in [self.ERR_NOT_EXIST, self.ERR_INVALID]

        self._repo = repo
        self._name = name
        self._path = path
        self._err = err

    def __str__(self):
        if self._err == self.ERR_NOT_EXIST:
            return "nonexistent profile %s (%s) in %s" % (self._name, self._path, self._repo)
        elif self._err == self.ERR_INVALID:
            return "invalid profile %s (%s) in %s" % (self._name, self._path, self._repo)
        else:
            assert False


class ProfilePropertyFileParseError(ProfileError):
    """Profile property file parse failed."""

    def __init__(self, profile, property_filename, error, line=None, lineno=None):
        # no performance concern is needed for exception object

        assert isinstance(profile, Profile)
        assert isinstance(property_filename, str) and "/" not in property_filename
        assert isinstance(error, str)
        if line is not None:
            assert isinstance(line, str)
            assert isinstance(lineno, int)
        else:
            assert lineno is None

        self._profile = profile
        self._filename = property_filename
        self._error = error
        self._line = line
        self._lineno = lineno

    def __str__(self):
        ret = "failed parsing %s in %s: %s" % (self._filename, self._profile, self._error)
        if line is not None:
            ret += ", line %d: %s" % (self._lineno, self._line)
        return ret


def _profile_path(repo, profile_name):
    return pjoin(repo.location, "profiles", profile_name)


def _decorator_helper(op, profile, property_filename, eapi_optional):
    # op == 1: get property file path
    # op == 2: read content from property file
    # op == 3: read lines from property file

    if eapi_optional is not None and not getattr(profile.eapi.options, eapi_optional, None):
        if op == 1 or op == 2:
            return None
        elif op == 3:
            return ()
        else:
            assert False
    else:
        property_filepath = pjoin(_profile_path(profile._repo, profile._name), property_filename)
        if not os.path.exists(property_filepath):
            if op == 1 or op == 2:
                return None
            elif op == 3:
                return ()
            else:
                assert False
        else:
            if op == 1:
                return property_filepath
            elif op == 2:
                return pathlib.Path(property_filepath).read_text()
            elif op == 3:
                return iter_read_bash(property_filepath, enum_line=True)
            else:
                assert False
