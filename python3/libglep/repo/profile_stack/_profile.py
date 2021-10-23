import os
from snakeoil import klass
from snakeoil.bash import iter_read_bash, read_bash_dict



def _read_profile_files(files, allow_line_cont=False):
    """Read all the given data files."""
    for path in files:
        # determine file path relative to the profiles dir
        try:
            relpath = path.split('/profiles/')[1]
        except IndexError:
            # profiles base path
            relpath = os.path.basename(path)

        for lineno, line in iter_read_bash(path, allow_line_cont=allow_line_cont, enum_line=True):
            yield line, lineno, relpath


def load_property(filename, *, read_func=_read_profile_files, fallback=(),
                  parse_func=lambda x: x, allow_line_cont=False, allow_recurse=False,
                  eapi_optional=None):
    """Decorator simplifying parsing profile files to generate a profile property.

    :param filename: The filename to parse within that profile directory.
    :keyword read_func: An invokable used to read the specified file.
    :keyword fallback: What to return if the file does not exist for this profile. Must be immutable.
    :keyword parse_func: An invokable used to parse the data.
    :keyword allow_line_cont: Controls whether line continuations are respected.
    :keyword allow_recurse: Controls whether or not this specific content can be a directory
        of files, rather than just a file.  Only is consulted if we're parsing the profile
        in non pms strict mode.
    :keyword fallback: What to return if the file does not exist for this profile. Must be immutable.
    :keyword eapi_optional: If given, the EAPI for this profile node is checked to see if
        the given optional evaluates to True; if so, then parsing occurs.  If False, then
        the fallback is returned and no ondisk activity occurs.
    :return: A :py:`klass.jit.attr_named` property instance.
    """
    def f(func):
        f2 = klass.jit_attr_named(f'_{func.__name__}')
        return f2(partial(_load_and_invoke, func, filename, read_func, fallback, allow_recurse, allow_line_cont, parse_func, eapi_optional))
    return f


def _load_and_invoke(func, filename, read_func, fallback, allow_recurse, allow_line_cont, parse_func, eapi_optional, self):
    if eapi_optional is not None and not getattr(self.eapi.options, eapi_optional, None):
        return func(self, fallback)

    profile_path = self.path.rstrip('/')
    base = pjoin(profile_path, filename)

    files = []
    if self.pms_strict or not allow_recurse:
        if os.path.exists(base):
            files.append(base)
    else:
        # Skip hidden files and backup files, those beginning with '.' or
        # ending with '~', respectively.
        files.extend(sorted_scan(base, hidden=False, backup=False))

    try:
        if files:
            if read_func is None:
                data = parse_func(files)
            else:
                data = parse_func(read_func(files, allow_line_cont=allow_line_cont))
        else:
            data = fallback
        return func(self)
    except (ValueError, IndexError, EnvironmentError) as e:
        raise ProfileError(profile_path, filename, e) from e
    except IsADirectoryError as e:
        raise ProfileError(
            self.path, filename,
            "path is a directory, but this profile is PMS format- "
            "directories aren't allowed. See layout.conf profile-formats "
            "to enable directory support") from e






class Profile(metaclass=klass.immutable_instance):

    _repo_map = None

    def __init__(self, repo, path, pms_strict=True):
        self._repo = repo
        self._name = path
        self.path = os.path.join(self._repo.location, "profiles", self._name)
        self.pms_strict = pms_strict

        if not os.path.isdir(self.path):
            raise ProfileNotExistError(self.path)

    def __str__(self):
        return f"profile {self._name} for repo {self._repo}"

    def __repr__(self):
        return '<%s repo=%r, name=%r, @%#8x>' % (self.__class__.__name__, self._repo, self._name, id(self))

    @klass.jit_attr
    def name(self):
        return self._name

    @klass.jit_attr
    def packages(self):
        # TODO: get profile-set support into PMS
        profile_set = 'profile-set' in self._repo.profile_formats
        sys, neg_sys, pro, neg_pro = [], [], [], []
        neg_wildcard = False
        for line, lineno, relpath in self._read_profile_property_file("packages"):
            try:
                if line[0] == '-':
                    if line == '-*':
                        neg_wildcard = True
                    elif line[1] == '*':
                        neg_sys.append(self.eapi_atom(line[2:]))
                    elif profile_set:
                        neg_pro.append(self.eapi_atom(line[1:]))
                    else:
                        logger.error(f'{relpath!r}: invalid line format, line {lineno}: {line!r}')
                else:
                    if line[0] == '*':
                        sys.append(self.eapi_atom(line[1:]))
                    elif profile_set:
                        pro.append(self.eapi_atom(line))
                    else:
                        logger.error(f'{relpath!r}: invalid line format, line {lineno}: {line!r}')
            except ebuild_errors.MalformedAtom as e:
                logger.error(f'{relpath!r}, line {lineno}: parsing error: {e}')
        system = [tuple(neg_sys), tuple(sys)]
        profile = [tuple(neg_pro), tuple(pro)]
        if neg_wildcard:
            system.append(neg_wildcard)
            profile.append(neg_wildcard)
        return _Packages(tuple(system), tuple(profile))

    @klass.jit_attr
    def parent_paths(self):
        data = self._read_profile_property_file("parents")
        if 'portage-2' in self._repo.profile_formats:
            l = []
            for line, lineno, relpath in data:
                repo_id, separator, profile_path = line.partition(':')
                if separator:
                    if repo_id:
                        try:
                            location = self._repo_map[repo_id]
                        except KeyError:
                            # check if requested repo ID matches the current
                            # repo which could be the case when running against
                            # unconfigured, external repos.
                            if repo_id == repo_config.repo_id:
                                location = repo_config.location
                            else:
                                logger.error(
                                    f'repo {repo_config.repo_id!r}: '
                                    f"{relpath!r} (line {lineno}), "
                                    f'bad profile parent {line!r}: '
                                    f'unknown repo {repo_id!r}'
                                )
                                continue
                    l.append((abspath(pjoin(location, 'profiles', profile_path)), line, lineno))
                else:
                    l.append((abspath(pjoin(self.path, repo_id)), line, lineno))
            return tuple(l)
        else:
            return tuple((abspath(pjoin(self.path, line)), line, lineno)
                        for line, lineno, relpath in data)

    @klass.jit_attr
    def pkg_provided(self):
        for line, lineno, relpath in self._read_profile_property_file("package.provided", eapi_optional='profile_pkg_provided'):
            try:
                yield CPV(line)
            except errors.InvalidCPV:
                raise ParseError(f'invalid package.provided entry: {line}')

    @klass.jit_attr
    def masks(self):
        data = self._read_profile_property_file("package.mask")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def unmasks(self):
        data = self._read_profile_property_file("package.unmask")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def pkg_deprecated(self):
        data = self._read_profile_property_file("package.deprecated")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def keywords(self):
        data = self._read_profile_property_file("package.keywords")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def accept_keywords(self):
        data = self._read_profile_property_file("package.accept_keywords")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def pkg_use(self):
        data = self._read_profile_property_file("package.use")
        c = ChunkedDataDict()
        c.update_from_stream(chain.from_iterable(self._parse_package_use(data).values()))
        c.freeze()
        return c

    @klass.jit_attr
    def deprecated(self):
        path = os.path.join(self.path, "deprecated")
        try:
            data = pathlib.Path(path).read_text()
            i = data.find("\n")
            if i < 0:
                raise ParseError(f"deprecated profile missing replacement: '{self.name}/deprecated'")
            if len(data) > i + 1 and data[i+1] != "\n":
                raise ParseError(f"deprecated profile missing message: '{self.name}/deprecated'")
            replacement = data[:i]          # replacement is in the line 1
            msg = data[i+2:]                # line 2 is empty, line 3 and the following is the message
            return (replacement, msg)
        except FileNotFoundError:
            return None

    @klass.jit_attr
    def use_force(self):
        data = self._read_profile_property_file("use.force")
        return self._parse_use(data)

    @klass.jit_attr
    def use_stable_force(self):
        data = self._read_profile_property_file("use.stable.force", eapi_optional='profile_stable_use')
        return self._parse_use(data)

    @klass.jit_attr
    def pkg_use_force(self):
        data = self._read_profile_property_file("package.use.force")
        return self._parse_package_use(data)

    @klass.jit_attr
    def pkg_use_stable_force(self):
        data = self._read_profile_property_file("package.use.stable.force", eapi_optional='profile_stable_use')
        return self._parse_package_use(data)

    @klass.jit_attr
    def use_mask(self):
        data = self._read_profile_property_file("use.mask")
        return self._parse_use(data)

    @klass.jit_attr
    def use_stable_mask(self):
        data = self._read_profile_property_file("use.stable.mask", eapi_optional='profile_stable_use')
        return self._parse_use(data)

    @klass.jit_attr
    def pkg_use_mask(self):
        data = self._read_profile_property_file("package.use.mask")
        return self._parse_package_use(data)

    @klass.jit_attr
    def pkg_use_stable_mask(self):
        data = self._read_profile_property_file("package.use.stable.mask", eapi_optional='profile_stable_use')
        return self._parse_package_use(data)

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
    def make_defaults(self):
        data = self._read_profile_property_file("make.defaults", fallback=None)
        d = {}
        if data is not None:
            d.update(read_bash_dict(data[0]))
        return ImmutableDict(d)

    @klass.jit_attr
    def default_env(self):
        data = self._read_profile_property_file("make.defaults", fallback=None)
        rendered = _make_incrementals_dict()
        for parent in self.parents:
            rendered.update(parent.default_env.items())

        if data is not None:
            data = read_bash_dict(data[0], vars_dict=rendered)
            rendered.update(data.items())
        return ImmutableDict(rendered)

    @klass.jit_attr
    def bashrc(self):
        path = pjoin(self.path, "profile.bashrc")
        if os.path.exists(path):
            return local_source(path)
        return None

    @klass.jit_attr
    def eapi(self):
        fullfn = os.path.join(self.path, "eapi")
        if not os.path.exists(fullfn):
            return "0"
        return pathlib.Path(fullfn).read_text().rstrip("\n")

    def _read_profile_property_file(self, filename, eapi_optional=None, fallback=()):
        """
        :filename: str property file name
        :keyword fallback: What to return if the file does not exist for this profile. Must be immutable.
        :keyword eapi_optional: If given, the EAPI for this profile node is checked to see if
            the given optional evaluates to True; if so, then parsing occurs.  If False, then
            the fallback is returned and no ondisk activity occurs.
        """
        if eapi_optional is not None and not getattr(self.eapi.options, eapi_optional, None):
            data = fallback
        else:
            path = os.path.join(self.path, filename)
            if not os.path.exists(path):
                data = fallback
            else:
                data = iter_read_bash(path, enum_line=True)
        for lineno, line in data:
            yield line, lineno, filename

    def _parse_atom_negations(self):
        """Parse files containing optionally negated package atoms."""
        neg, pos = [], []
        for line, lineno, relpath in data:
            if line[0] == '-':
                line = line[1:]
                if not line:
                    logger.error(f"{relpath!r}, line {lineno}: '-' negation without an atom")
                    continue
                l = neg
            else:
                l = pos
            try:
                l.append(self.eapi_atom(line))
            except ebuild_errors.MalformedAtom as e:
                logger.error(f'{relpath!r}, line {lineno}: parsing error: {e}')
        return tuple(neg), tuple(pos)

    def _package_keywords_splitter(self, iterable):
        """Parse package keywords files."""
        for line, lineno, relpath in iterable:
            v = line.split()
            try:
                yield (atom(v[0]), tuple(stable_unique(v[1:])))
            except ebuild_errors.MalformedAtom as e:
                logger.error(f'{relpath!r}, line {lineno}: parsing error: {e}')

    def _parse_package_use(self):
        d = defaultdict(list)
        # split the data down ordered cat/pkg lines
        for line, lineno, relpath in data:
            l = line.split()
            try:
                a = self.eapi_atom(l[0])
            except ebuild_errors.MalformedAtom as e:
                logger.error(f'{relpath!r}, line {lineno}: parsing error: {e}')
                continue
            if len(l) == 1:
                logger.error(f'{relpath!r}, line {lineno}: missing USE flag(s): {line!r}')
                continue
            d[a.key].append(misc.chunked_data(a, *split_negations(l[1:])))

        return ImmutableDict((k, misc._build_cp_atom_payload(v, atom(k)))
                             for k, v in d.items())

    def _parse_use(self):
        c = misc.ChunkedDataDict()
        data = (x[0] for x in data)
        neg, pos = split_negations(data)
        if neg or pos:
            c.add_bare_global(neg, pos)
        c.freeze()
        return c


class ProfileStack:

    def __init__(self, repo, name):
        self._repo = repo

        # current profile is the first element in self._profiles
        self._profiles = []
        self._add_profile_and_its_ancestors(name)
        self._profiles.reverse()

    def name(self):
        return self._profile[0]._name

    def packages(self):
        return self._profiles[0].packages

    @klass.jit_attr
    def pkg_provided(self):
        for p in self._profiles:
            for cpv in p.pkg_provided:
                yield cpv

o    @klass.jit_attr
    def masks(self):
        data = self._read_profile_property_file("package.mask")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def unmasks(self):
        data = self._read_profile_property_file("package.unmask")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def pkg_deprecated(self):
        data = self._read_profile_property_file("package.deprecated")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def keywords(self):
        data = self._read_profile_property_file("package.keywords")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def accept_keywords(self):
        data = self._read_profile_property_file("package.accept_keywords")
        return self._parse_atom_negations(data)

    @klass.jit_attr
    def pkg_use(self):
        data = self._read_profile_property_file("package.use")
        c = ChunkedDataDict()
        c.update_from_stream(chain.from_iterable(self._parse_package_use(data).values()))
        c.freeze()
        return c

    @klass.jit_attr
    def deprecated(self):
        if self._profiles[0].deprecated:
            return True
        else:
            for p in self._profiles[1:]:
                if p.deprecated:
                    raise ParseError(f"parent profile {p.name} of profile {self.name} is deprecated")
            return False

    @klass.jit_attr
    def use_force(self):
        data = self._read_profile_property_file("use.force")
        return self._parse_use(data)

    @klass.jit_attr
    def use_stable_force(self):
        data = self._read_profile_property_file("use.stable.force", eapi_optional='profile_stable_use')
        return self._parse_use(data)

    @klass.jit_attr
    def pkg_use_force(self):
        data = self._read_profile_property_file("package.use.force")
        return self._parse_package_use(data)

    @klass.jit_attr
    def pkg_use_stable_force(self):
        data = self._read_profile_property_file("package.use.stable.force", eapi_optional='profile_stable_use')
        return self._parse_package_use(data)

    @klass.jit_attr
    def use_mask(self):
        data = self._read_profile_property_file("use.mask")
        return self._parse_use(data)

    @klass.jit_attr
    def use_stable_mask(self):
        data = self._read_profile_property_file("use.stable.mask", eapi_optional='profile_stable_use')
        return self._parse_use(data)

    @klass.jit_attr
    def pkg_use_mask(self):
        data = self._read_profile_property_file("package.use.mask")
        return self._parse_package_use(data)

    @klass.jit_attr
    def pkg_use_stable_mask(self):
        data = self._read_profile_property_file("package.use.stable.mask", eapi_optional='profile_stable_use')
        return self._parse_package_use(data)

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
    def make_defaults(self):
        data = self._read_profile_property_file("make.defaults", fallback=None)
        d = {}
        if data is not None:
            d.update(read_bash_dict(data[0]))
        return ImmutableDict(d)

    @klass.jit_attr
    def default_env(self):
        data = self._read_profile_property_file("make.defaults", fallback=None)
        rendered = _make_incrementals_dict()
        for parent in self.parents:
            rendered.update(parent.default_env.items())

        if data is not None:
            data = read_bash_dict(data[0], vars_dict=rendered)
            rendered.update(data.items())
        return ImmutableDict(rendered)

    @klass.jit_attr
    def bashrc(self):
        return self._profiles[0].profile.bashrc

    @klass.jit_attr
    def eapi(self):
        fullfn = os.path.join(self.path, "eapi")
        if not os.path.exists(fullfn):
            return "0"
        return pathlib.Path(fullfn).read_text().rstrip("\n")






    def _add_profile_and_its_ancestors(self, name):
        pobj = Profile(self._repo, name)
        for p in pobj.parents:
            if p not in self._profiles:
                self._profiles.append(p)
        self._profiles.append(pobj)

    def _combine_all_profiles_property(self, property_name):
        








    deprecated = klass.alias_attr("node.deprecated")
    eapi = klass.alias_attr("node.eapi")
    name = klass.alias_attr("node.name")

    @klass.jit_attr
    def stack(self):
        def f(node):
            for path, line, lineno in node.parent_paths:
                try:
                    x = self.RawProfile._autodetect_and_create(path)
                except ProfileError as e:
                    repo_id = node.repoconfig.repo_id
                    logger.error(
                        f"repo {repo_id!r}: '{self.name}/parent' (line {lineno}), "
                        f'bad profile parent {line!r}: {e.error}'
                    )
                    continue
                for y in f(x):
                    yield y
            yield node
        return tuple(f(self.node))

    @klass.jit_attr
    def _system_profile(self):
        """User-selected system profile.

        This should map directly to the profile linked to /etc/portage/make.profile.
        """
        # prefer main system profile; otherwise, fallback to custom user profile
        for profile in reversed(self.stack):
            if not isinstance(profile, UserProfileNode):
                break
        return profile

    def _collapse_use_dict(self, attr):
        stack = (getattr(x, attr) for x in self.stack)
        d = misc.ChunkedDataDict()
        for mapping in stack:
            d.merge(mapping)
        d.freeze()
        return d

    @klass.jit_attr
    def forced_use(self):
        return self._collapse_use_dict("forced_use")

    @klass.jit_attr
    def masked_use(self):
        return self._collapse_use_dict("masked_use")

    @klass.jit_attr
    def stable_forced_use(self):
        return self._collapse_use_dict("stable_forced_use")

    @klass.jit_attr
    def stable_masked_use(self):
        return self._collapse_use_dict("stable_masked_use")

    @klass.jit_attr
    def pkg_use(self):
        return self._collapse_use_dict("pkg_use")

    def _collapse_generic(self, attr, clear=False):
        s = set()
        for node in self.stack:
            val = getattr(node, attr)
            if clear and len(val) > 2 and val[2]:
                s.clear()
            s.difference_update(val[0])
            s.update(val[1])
        return s

    @klass.jit_attr
    def default_env(self):
        d = dict(self.node.default_env.items())
        for incremental in const.incrementals:
            v = d.pop(incremental, '').split()
            if v:
                if incremental in const.incrementals_unfinalized:
                    d[incremental] = tuple(v)
                else:
                    v = misc.incremental_expansion(
                        v, msg_prefix=f"While expanding {incremental}, value {v!r}: ")
                    if v:
                        d[incremental] = tuple(v)
        return ImmutableDict(d.items())

    @property
    def profile_only_variables(self):
        if "PROFILE_ONLY_VARIABLES" in const.incrementals:
            return frozenset(self.default_env.get("PROFILE_ONLY_VARIABLES", ()))
        return frozenset(self.default_env.get("PROFILE_ONLY_VARIABLES", "").split())

    @klass.jit_attr
    def use_expand(self):
        """USE_EXPAND variables defined by the profile."""
        if "USE_EXPAND" in const.incrementals:
            return frozenset(self.default_env.get("USE_EXPAND", ()))
        return frozenset(self.default_env.get("USE_EXPAND", "").split())

    @klass.jit_attr
    def use(self):
        """USE flag settings for the profile."""
        return tuple(list(self.default_env.get('USE', ())) + list(self.expand_use()))

    def expand_use(self, env=None):
        """Expand USE_EXPAND settings to USE flags."""
        if env is None:
            env = self.default_env

        use = []
        for u in self.use_expand:
            value = env.get(u)
            if value is None:
                continue
            u2 = u.lower() + '_'
            use.extend(u2 + x for x in value.split())
        return tuple(use)

    @property
    def use_expand_hidden(self):
        if "USE_EXPAND_HIDDEN" in const.incrementals:
            return frozenset(self.default_env.get("USE_EXPAND_HIDDEN", ()))
        return frozenset(self.default_env.get("USE_EXPAND_HIDDEN", "").split())

    @property
    def iuse_implicit(self):
        if "IUSE_IMPLICIT" in const.incrementals:
            return frozenset(self.default_env.get("IUSE_IMPLICIT", ()))
        return frozenset(self.default_env.get("IUSE_IMPLICIT", "").split())

    @property
    def use_expand_implicit(self):
        if "USE_EXPAND_IMPLICIT" in const.incrementals:
            return frozenset(self.default_env.get("USE_EXPAND_IMPLICIT", ()))
        return frozenset(self.default_env.get("USE_EXPAND_IMPLICIT", "").split())

    @property
    def use_expand_unprefixed(self):
        if "USE_EXPAND_UNPREFIXED" in const.incrementals:
            return frozenset(self.default_env.get("USE_EXPAND_UNPREFIXED", ()))
        return frozenset(self.default_env.get("USE_EXPAND_UNPREFIXED", "").split())

    @klass.jit_attr
    def iuse_effective(self):
        iuse_effective = []

        # EAPI 5 and above allow profile defined IUSE injection (see PMS)
        if self._system_profile.eapi.options.profile_iuse_injection:
            iuse_effective.extend(self.iuse_implicit)
            for v in self.use_expand_implicit.intersection(self.use_expand_unprefixed):
                iuse_effective.extend(self.default_env.get("USE_EXPAND_VALUES_" + v, "").split())
            for v in self.use_expand.intersection(self.use_expand_implicit):
                for x in self.default_env.get("USE_EXPAND_VALUES_" + v, "").split():
                    iuse_effective.append(v.lower() + "_" + x)
        else:
            iuse_effective.extend(self._system_profile.repoconfig.known_arches)
            for v in self.use_expand:
                for x in self.default_env.get("USE_EXPAND_VALUES_" + v, "").split():
                    iuse_effective.append(v.lower() + "_" + x)

        return frozenset(iuse_effective)

    @klass.jit_attr
    def provides_repo(self):
        # delay importing to avoid circular imports
        from .repository import ProvidesRepo
        return ProvidesRepo(pkgs=self._collapse_generic("pkg_provided"))

    @klass.jit_attr
    def masks(self):
        return frozenset(chain(self._collapse_generic("masks")))

    @klass.jit_attr
    def unmasks(self):
        return frozenset(self._collapse_generic('unmasks'))

    @klass.jit_attr
    def pkg_deprecated(self):
        return frozenset(chain(self._collapse_generic("pkg_deprecated")))

    @klass.jit_attr
    def keywords(self):
        return tuple(chain.from_iterable(x.keywords for x in self.stack))

    @klass.jit_attr
    def accept_keywords(self):
        return tuple(chain.from_iterable(x.accept_keywords for x in self.stack))

    def _incremental_masks(self, stack_override=None):
        if stack_override is None:
            stack_override = self.stack
        return tuple(node.masks for node in stack_override if any(node.masks))

    def _incremental_unmasks(self, stack_override=None):
        if stack_override is None:
            stack_override = self.stack
        return tuple(node.unmasks for node in stack_override if any(node.unmasks))

    @klass.jit_attr
    def bashrcs(self):
        return tuple(x.bashrc for x in self.stack if x.bashrc is not None)

    bashrc = klass.alias_attr("bashrcs")
    path = klass.alias_attr("node.path")

    @klass.jit_attr
    def system(self):
        return frozenset(self._collapse_generic('system', clear=True))

    @klass.jit_attr
    def profile_set(self):
        return frozenset(self._collapse_generic('profile_set', clear=True))
