from snakeoil import klass
from snakeoil.osutils import pjoin
from snakeoil.bash import read_dict, iter_read_bash
from snakeoil.fileutils import readlines
from snakeoil.sequences import iter_stable_unique
from snakeoil.strings import pluralism

from . import Manifests


class LayoutConfFile(klass.ImmutableInstance):

    __slots__ = ("repo_name", "manifests", "masters", "aliases", "properties_allowed", "restrict_allowed", 
                 "eapis_banned", "eapis_deprecated", "sign_commits", "cache_format", "profile_formats", "_repo")

    def __init__(self, path):
        """Load data from the repo's metadata/layout.conf file."""

        sf = object.__setattr__
        data = read_dict(iter_read_bash(readlines(path, strip_whitespace=True, swallow_missing=True)),
                         source_isiter=True,
                         strip=True,
                         filename=path,
                         ignore_errors=True)

        # self.repo_name
        sf(self, 'repo_name', data.get('repo-name', None))

        # self.manifests
        manifests = Manifests()
        if True:
            manifest_policy = data.get('use-manifests', 'strict').lower()

            manifests.disabled = (manifest_policy == 'false')
            manifests.strict = (manifest_policy == 'strict')
            manifests.thin = (data.get('thin-manifests', '').lower() == 'true')
            manifests.signed = (data.get('sign-manifests', 'true').lower() == 'true'),

            manifests.hashes = data.get('manifest-hashes', '').lower().split()
            if manifests.hashes:
                manifests.hashes = ['size'] + manifests.hashes
                manifests.hashes = tuple(iter_stable_unique(manifests.hashes))
            else:
                manifests.hashes = _default_hashes

            manifests.required_hashes = data.get('manifest-required-hashes', '').lower().split()
            if manifests.required_hashes:
                manifests.required_hashes = ['size'] + manifests.required_hashes
                manifests.required_hashes = tuple(iter_stable_unique(manifests.required_hashes))
            else:
                manifests.required_hashes = _default_required_hashes
        sf(self, 'manifests', manifests)

        # self.masters
        masters = data.get('masters')
        if masters is None:
            masters = ()
        else:
            masters = tuple(masters.split())        # FIXME: check duplicated items and raise exception
        sf(self, 'masters', masters)

        # self.aliases
        # FIXME
        aliases = data.get('aliases', '').split() + [self.config_name, self.repo_name, self.pms_repo_name, self.location]
        sf(self, 'aliases', tuple(filter(None, aliases)))                                   # FIXME: unique check and raise exception

        # properties_allowed, restrict_allowed
        sf(self, 'properties_allowed', tuple(data.get('properties-allowed', '').split()))   # FIXME: unique check and raise exception
        sf(self, 'restrict_allowed', tuple(data.get('restrict-allowed', '').split()))       # FIXME: unique check and raise exception

        # self.eapi_banned, self.eapi_deprecated
        sf(self, 'eapis_banned', tuple(data.get('eapis-banned', '').split()))               # FIXME: unique check and raise exception
        sf(self, 'eapis_deprecated', tuple(data.get('eapis-deprecated', '').split()))       # FIXME: unique check and raise exception

        # self._sign_commits
        sf(self, 'sign_commits', data.get('sign-commits', 'false').lower() == 'true')

        # self.cache_format
        cache_formats = set(data.get('cache-formats', 'md5-dict').lower().split())
        if not cache_formats:
            cache_formats = [None]
        else:
            for f in cache_formats:
                if f not in _supported_cache_formats:
                    raise ParseError("unsupporte cache format %s" % (f))
            cache_formats = [f for f in _supported_cache_formats if f in cache_formats]     # sort into favored order
        sf(self, 'cache_format', list(cache_formats)[0])

        # self.profile_formats
        profile_formats = set(data.get('profile-formats', 'pms').lower().split())
        if not profile_formats:
            raise ParseError(f"{self.repo} has explicitly unset profile-formats")
        unknown = profile_formats.difference(_supported_profile_formats)
        if unknown:
            raise ParseError(f"{self.repo} has unsupported profile format%s: %s" % (pluralism(unknown), ', '.join(sorted(unknown))))
        sf(self, 'profile_formats', profile_formats)


_default_hashes = ('size', 'blake2b', 'sha512')
_default_required_hashes = ('size', 'blake2b')
_supported_profile_formats = ('pms', 'portage-1', 'portage-2', 'profile-set')
_supported_cache_formats = ('md5-dict', 'pms')
