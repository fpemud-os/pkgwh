

class UnconfiguredTree(prototype.tree):
    """Raw implementation supporting standard ebuild tree.

    Return packages don't have USE configuration bound to them.
    """

    false_categories = frozenset(["eclass", "profiles", "metadata", "licenses"])
    configured = False
    configurables = ("domain", "settings")
    package_factory = staticmethod(ebuild_src.generate_new_factory)
    enable_gpg = False
    extension = '.ebuild'

    operations_kls = repo_operations

    pkgcore_config_type = ConfigHint({
        'location': 'str',
        'eclass_cache': 'ref:eclass_cache',
        'masters': 'refs:repo',
        'cache': 'refs:cache',
        'default_mirrors': 'list',
        'allow_missing_manifests': 'bool',
        'repo_config': 'ref:repo_config',
        },
        typename='repo')

    def __init__(self, location, eclass_cache=None, masters=(), cache=(),
                 default_mirrors=None, allow_missing_manifests=False, package_cache=True,
                 repo_config=None):
        """
        :param location: on disk location of the tree
        :param cache: sequence of :obj:`pkgcore.cache.template.database` instances
            to use for storing metadata
        :param masters: repo masters this repo inherits from
        :param eclass_cache: If not None, :obj:`pkgcore.ebuild.eclass_cache`
            instance representing the eclasses available,
            if None, generates the eclass_cache itself
        :param default_mirrors: Either None, or sequence of mirrors to try
            fetching from first, then falling back to other uri
        :param package_cache: boolean controlling package instance caching
        :param repo_config: :obj:`pkgcore.repo_objs.RepoConfig` instance for the related repo
        """
        super().__init__()
        self.base = self.location = location
        self.package_cache = package_cache
        if repo_config is None:
            repo_config = repo_objs.RepoConfig(location)
        self.config = repo_config

        # profiles dir is required by PMS
        if not os.path.isdir(self.config.profiles_base):
            raise errors.InvalidRepo(f'missing required profiles dir: {self.location!r}')

        # verify we support the repo's EAPI
        if not self.is_supported:
            raise errors.UnsupportedRepo(self)

        if eclass_cache is None:
            eclass_cache = eclass_cache_mod.cache(
                pjoin(self.location, 'eclass'), location=self.location)
        self.eclass_cache = eclass_cache

        self.masters = tuple(masters)
        self.trees = self.masters + (self,)
        self.licenses = repo_objs.Licenses(self.location)
        self.profiles = self.config.profiles
        if masters:
            self.licenses = repo_objs.OverlayedLicenses(*self.trees)
            self.profiles = repo_objs.OverlayedProfiles(*self.trees)

        # use mirrors from masters if not defined in the repo
        mirrors = dict(self.thirdpartymirrors)
        for master in masters:
            for k, v in master.mirrors.items():
                if k not in mirrors:
                    mirrors[k] = v

        if isinstance(cache, (tuple, list)):
            cache = tuple(cache)
        else:
            cache = (cache,)

        self.mirrors = mirrors
        self.default_mirrors = default_mirrors
        self.cache = cache
        self._allow_missing_chksums = allow_missing_manifests
        self.package_class = self.package_factory(
            self, cache, self.eclass_cache, self.mirrors, self.default_mirrors)
        self._shared_pkg_cache = WeakValueDictionary()
        self._bad_masked = RestrictionRepo(repo_id='bad_masked')
        self.projects_xml = repo_objs.LocalProjectsXml(
            pjoin(self.location, 'metadata', 'projects.xml'))

    repo_id = klass.alias_attr('config.repo_id')
    repo_name = klass.alias_attr('config.repo_name')
    aliases = klass.alias_attr('config.aliases')
    eapi = klass.alias_attr('config.eapi')
    is_supported = klass.alias_attr('config.eapi.is_supported')
    external = klass.alias_attr('config.external')
    pkg_masks = klass.alias_attr('config.pkg_masks')

    def configure(self, *args):
        return ConfiguredTree(self, *args)

    @klass.jit_attr
    def known_arches(self):
        """Return all known arches for a repo (including masters)."""
        return frozenset(chain.from_iterable(
            r.config.known_arches for r in self.trees))

    def path_restrict(self, path):
        """Return a restriction from a given path in a repo.

        :param path: full or partial path to an ebuild
        :return: a package restriction matching the given path if possible
        :raises ValueError: if the repo doesn't contain the given path, the
            path relates to a file that isn't an ebuild, or the ebuild isn't in the
            proper directory layout
        """
        if path not in self:
            raise ValueError(f"{self.repo_id!r} repo doesn't contain: {path!r}")

        if not path.startswith(os.sep) and os.path.exists(pjoin(self.location, path)):
            path_chunks = path.split(os.path.sep)
        else:
            path = os.path.realpath(os.path.abspath(path))
            relpath = path[len(os.path.realpath(self.location)):].strip('/')
            path_chunks = relpath.split(os.path.sep)

        if os.path.isfile(path):
            if not path.endswith('.ebuild'):
                raise ValueError(f"file is not an ebuild: {path!r}")
            elif len(path_chunks) != 3:
                # ebuild isn't in a category/PN directory
                raise ValueError(
                    f"ebuild not in the correct directory layout: {path!r}")

        restrictions = []

        # add restrictions until path components run out
        try:
            restrictions.append(restricts.RepositoryDep(self.repo_id))
            if path_chunks[0] in self.categories:
                restrictions.append(restricts.CategoryDep(path_chunks[0]))
                restrictions.append(restricts.PackageDep(path_chunks[1]))
                base = cpv.VersionedCPV(f"{path_chunks[0]}/{os.path.splitext(path_chunks[2])[0]}")
                restrictions.append(restricts.VersionMatch('=', base.version, rev=base.revision))
        except IndexError:
            pass
        return packages.AndRestriction(*restrictions)

    def __getitem__(self, cpv):
        cpv_inst = self.package_class(*cpv)
        if cpv_inst.fullver not in self.versions[(cpv_inst.category, cpv_inst.package)]:
            raise KeyError(cpv)
        return cpv_inst

    def rebind(self, **kwds):
        """Generate a new tree instance with the same location using new keywords.

        :param kwds: see __init__ for valid values
        """
        o = self.__class__(self.location, **kwds)
        o.categories = self.categories
        o.packages = self.packages
        o.versions = self.versions
        return o

    @klass.jit_attr
    def thirdpartymirrors(self):
        mirrors = {}
        fp = pjoin(self.location, 'profiles', 'thirdpartymirrors')
        try:
            for k, v in read_dict(fp, splitter=None).items():
                v = v.split()
                # shuffle mirrors so the same ones aren't used every time
                shuffle(v)
                mirrors[k] = v
        except FileNotFoundError:
            pass
        return ImmutableDict(mirrors)

    @klass.jit_attr
    def use_expand_sort(self):
        """Inherited mapping of USE_EXPAND sorting keys for the repo."""
        d = {}
        for repo in self.trees:
            d.update(repo.config.use_expand_sort)
        return ImmutableDict(d)

    def use_expand_sorter(self, group):
        """Sorting function for a given USE_EXPAND group."""
        try:
            ordering = self.use_expand_sort[group.lower()]
            return lambda k: ordering.get(k, -1)
        except KeyError:
            # nonexistent USE_EXPAND group
            return lambda k: k

    @klass.jit_attr
    def category_dirs(self):
        try:
            return frozenset(map(intern, filterfalse(
                self.false_categories.__contains__,
                (x for x in listdir_dirs(self.base) if not x.startswith('.')))))
        except EnvironmentError as e:
            logger.error(f"failed listing categories: {e}")
        return ()

    def _get_categories(self, *optional_category):
        # why the auto return? current porttrees don't allow/support
        # categories deeper then one dir.
        if optional_category:
            # raise KeyError
            return ()
        categories = frozenset(chain.from_iterable(repo.config.categories for repo in self.trees))
        if categories:
            return categories
        return self.category_dirs

    def _get_packages(self, category):
        cpath = pjoin(self.base, category.lstrip(os.path.sep))
        try:
            return tuple(listdir_dirs(cpath))
        except FileNotFoundError:
            if category in self.categories:
                # ignore it, since it's PMS mandated that it be allowed.
                return ()
        except EnvironmentError as e:
            category = pjoin(self.base, category.lstrip(os.path.sep))
            raise KeyError(
                f'failed fetching packages for category {category}: {e}') from e

    def _get_versions(self, catpkg):
        """Determine available versions for a given package.

        Ebuilds with mismatched or invalid package names are ignored.
        """
        cppath = pjoin(self.base, catpkg[0], catpkg[1])
        pkg = f'{catpkg[-1]}-'
        lp = len(pkg)
        extension = self.extension
        ext_len = -len(extension)
        try:
            return tuple(
                x[lp:ext_len] for x in listdir_files(cppath)
                if x[ext_len:] == extension and x[:lp] == pkg)
        except EnvironmentError as e:
            raise KeyError(
                "failed fetching versions for package %s: %s" %
                (pjoin(self.base, '/'.join(catpkg)), str(e))) from e

    def _pkg_filter(self, raw, error_callback, pkgs):
        """Filter packages with bad metadata."""
        while True:
            try:
                pkg = next(pkgs)
            except pkg_errors.PackageError:
                # ignore pkgs with invalid CPVs
                continue
            except StopIteration:
                return

            if raw:
                yield pkg
            elif self._bad_masked.has_match(pkg.versioned_atom) and error_callback is not None:
                error_callback(self._bad_masked[pkg.versioned_atom])
            else:
                # check pkgs for unsupported/invalid EAPIs and bad metadata
                try:
                    if not pkg.is_supported:
                        exc = pkg_errors.MetadataException(
                            pkg, 'eapi', f"EAPI '{pkg.eapi}' is not supported")
                        self._bad_masked[pkg.versioned_atom] = exc
                        if error_callback is not None:
                            error_callback(exc)
                        continue
                    # TODO: add a generic metadata validation method to avoid slow metadata checks?
                    pkg.data
                    pkg.slot
                    pkg.required_use
                except pkg_errors.MetadataException as e:
                    self._bad_masked[e.pkg.versioned_atom] = e
                    if error_callback is not None:
                        error_callback(e)
                    continue
                yield pkg

    def itermatch(self, *args, **kwargs):
        raw = 'raw_pkg_cls' in kwargs or not kwargs.get('versioned', True)
        error_callback = kwargs.pop('error_callback', None)
        kwargs.setdefault('pkg_filter', partial(self._pkg_filter, raw, error_callback))
        return super().itermatch(*args, **kwargs)

    def _get_ebuild_path(self, pkg):
        return pjoin(
            self.base, pkg.category, pkg.package,
            f"{pkg.package}-{pkg.fullver}{self.extension}")

    def _get_ebuild_src(self, pkg):
        return local_source(self._get_ebuild_path(pkg), encoding='utf8')

    def _get_shared_pkg_data(self, category, package):
        key = (category, package)
        o = self._shared_pkg_cache.get(key)
        if o is None:
            mxml = self._get_metadata_xml(category, package)
            manifest = self._get_manifest(category, package)
            o = repo_objs.SharedPkgData(mxml, manifest)
            self._shared_pkg_cache[key] = o
        return o

    def _get_metadata_xml(self, category, package):
        return repo_objs.LocalMetadataXml(pjoin(
            self.base, category, package, "metadata.xml"))

    def _get_manifest(self, category, package):
        return digest.Manifest(pjoin(
            self.base, category, package, "Manifest"),
            thin=self.config.manifests.thin,
            enforce_gpg=self.enable_gpg)

    def _get_digests(self, pkg, allow_missing=False):
        if self.config.manifests.disabled:
            return True, {}
        try:
            manifest = pkg._shared_pkg_data.manifest
            manifest.allow_missing = allow_missing
            return allow_missing, manifest.distfiles
        except pkg_errors.ParseChksumError as e:
            if e.missing and allow_missing:
                return allow_missing, {}
            raise pkg_errors.MetadataException(pkg, 'manifest', str(e))

    def __repr__(self):
        return "<ebuild %s location=%r @%#8x>" % (
            self.__class__.__name__, self.base, id(self))

    @klass.jit_attr
    def deprecated(self):
        """Base deprecated packages restriction from profiles/package.deprecated."""
        return packages.OrRestriction(*self.config.pkg_deprecated)

    def _regen_operation_helper(self, **kwds):
        return _RegenOpHelper(
            self, force=bool(kwds.get('force', False)),
            eclass_caching=bool(kwds.get('eclass_caching', True)))

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['_shared_pkg_cache']
        return d

    def __setstate__(self, state):
        self.__dict__ = state.copy()
        self.__dict__['_shared_pkg_cache'] = WeakValueDictionary()


@configurable(
    typename='repo',
    types={
        'repo_config': 'ref:repo_config', 'cache': 'refs:cache',
        'eclass_cache': 'ref:eclass_cache',
        'default_mirrors': 'list',
        'allow_missing_manifests': 'bool'},
    requires_config='config')
def tree(config, repo_config, cache=(), eclass_cache=None,
         default_mirrors=None, allow_missing_manifests=False,
         tree_cls=UnconfiguredTree):
    """Initialize an unconfigured ebuild repository."""
    repo_id = repo_config.repo_id
    repo_path = repo_config.location

    if repo_config.masters is None:
        # if it's None, that means it's not a standalone, and is PMS, or misconfigured.
        # empty tuple means it's a standalone repository
        default = config.get_default('repo_config')
        if default is None:
            raise errors.InitializationError(
                f"repo {repo_id!r} at {repo_path!r} requires missing default repo")

    # map external repo ids to their config names
    config_map = {
        r.repo_id: r.location for r in config.objects['repo_config'].values() if r.external}

    try:
        masters = []
        missing = []
        for r in repo_config.masters:
            if repo := config.objects['repo'].get(config_map.get(r, r)):
                masters.append(repo)
            else:
                missing.append(r)
    except RecursionError:
        repo_id = repo_config.repo_id
        masters = ', '.join(repo_config.masters)
        raise errors.InitializationError(
            f'{repo_id!r} repo has cyclic masters: {masters}')

    if missing:
        missing = ', '.join(map(repr, sorted(missing)))
        raise errors.InitializationError(
            f'repo {repo_id!r} at path {repo_path!r} has missing masters: {missing}')

    if eclass_cache is None:
        eclass_cache = _sort_eclasses(config, repo_config)

    return tree_cls(
        repo_config.location, eclass_cache=eclass_cache, masters=masters, cache=cache,
        default_mirrors=default_mirrors,
        allow_missing_manifests=allow_missing_manifests,
        repo_config=repo_config)
