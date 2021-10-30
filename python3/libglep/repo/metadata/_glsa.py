import os
from lxml import etree
from snakeoil.osutils import pjoin, listdir_files
from ... import Repo
from .. import MetadataError

class GlsaDir:

    def __init__(self, repo):
        self._repo = repo
        self._path = pjoin(self._repo.location, _my_path)
        assert os.path.isdir(self._path)

    def iter_vulnerabilities(self):
        """generator yielding each GLSA restriction"""
        for fn in listdir_files(self._path):
            # glsa-1234-12.xml
            if not (fn.startswith("glsa-") and fn.endswith(".xml")):
                raise GlsaFileError(self._repo, f'invalid glsa file name: {fn!r}')
            # verifies the filename is of the correct syntax.
            try:
                [int(x) for x in fn[5:-4].split("-")]
            except ValueError:
                raise GlsaFileError(self._repo, f'invalid glsa file name: {fn!r}')

            root = etree.parse(pjoin(self._path, fn))
            glsa_node = root.getroot()
            if glsa_node.tag != 'glsa':
                raise GlsaFileError(self._repo, 'glsa file without glsa root node: {fn!r}')
            for affected in root.findall('affected'):
                for pkg in affected.findall('package'):
                    try:
                        pkgname = str(pkg.get('name')).strip()
                        pkg_vuln_restrict = self.generate_intersects_from_pkg_node(pkg, tag="glsa(%s)" % fn[5:-4])
                        if pkg_vuln_restrict is None:
                            continue
                        pkgatom = CP(pkgname)
                        yield fn[5:-4], pkgname, pkgatom, pkg_vuln_restrict
                    except InvalidCP as e:
                        raise GlsaFileError(self._repo, f"invalid glsa file {fn!r}, package {pkgname}: {e}")
                    except IGNORED_EXCEPTIONS:
                        raise
                    except Exception as e:
                        raise GlsaFileError(self._repo, f"invalid glsa file {fn!r}: {e}")


class GlsaFile:

    def __init__(self, repo, fn):
        self._repo = repo
        self._fn = fn
        self._cpDict = dict()

    @property
    def path(self):
        return pjoin(self._repo.location, _my_path, self._fn)

    @property
    def glsa_id(self):
        return self._fn[5:-4]

    def get_affected_packages(self):
        return self._cpDict.keys()



    def _parse(self):
        # glsa-1234-12.xml
        if not (self._fn.startswith("glsa-") and self._fn.endswith(".xml")):
            raise GlsaFileError(self._repo, f'invalid glsa file name: {self._fn!r}')

        # verifies the filename is of the correct syntax.
        try:
            [int(x) for x in self._fn[5:-4].split("-")]
        except ValueError:
            raise GlsaFileError(self._repo, f'invalid glsa file name: {self._fn!r}')

        glsa_node = etree.parse(self.path).getroot()
        if glsa_node.tag != 'glsa':
            raise GlsaFileError(self._repo, 'glsa file without glsa root node: {self._fn!r}')

        for affected in glsa_node.findall('affected'):
            for pkg in affected.findall('package'):
                try:
                    pkgname = str(pkg.get('name')).strip()
                    pkg_vuln_restrict = self._generate_intersects_from_pkg_node(pkg, tag="glsa(%s)" % self._fn[5:-4])
                    if pkg_vuln_restrict is None:
                        continue
                    self._cpDict[CP(pkgname)] = pkg_vuln_restrict
                except InvalidCP as e:
                    raise GlsaFileError(self._repo, f"invalid glsa file {self._fn!r}, package {pkgname}: {e}")
                except IGNORED_EXCEPTIONS:
                    raise
                except Exception as e:
                    raise GlsaFileError(self._repo, f"invalid glsa file {self._fn!r}: {e}")

    def _generate_intersects_from_pkg_node(self, pkg_node, tag=None):
        arch = pkg_node.get("arch")
        if arch is not None:
            arch = tuple(str(arch.strip()).split())
            if not arch or "*" in arch:
                arch = None

        vuln = list(pkg_node.findall("vulnerable"))
        if not vuln:
            return None
        elif len(vuln) > 1:
            vuln_list = [self._generate_restrict_from_range(x) for x in vuln]
            vuln = packages.OrRestriction(*vuln_list)
        else:
            vuln_list = [self._generate_restrict_from_range(vuln[0])]
            vuln = vuln_list[0]
        if arch is not None:
            vuln = packages.AndRestriction(vuln, packages.PackageRestriction(
                "keywords", values.ContainmentMatch2(arch, match_all=False)))
        invuln = (pkg_node.findall("unaffected"))
        if not invuln:
            # wrap it.
            return packages.KeyedAndRestriction(vuln, tag=tag)
        invuln_list = [self._generate_restrict_from_range(x, negate=True)
                       for x in invuln]
        invuln = [x for x in invuln_list if x not in vuln_list]
        if not invuln:
            if tag is None:
                return packages.KeyedAndRestriction(vuln, tag=tag)
            return packages.KeyedAndRestriction(vuln, tag=tag)
        return packages.KeyedAndRestriction(vuln, tag=tag, *invuln)

    def _generate_restrict_from_range(self, node, negate=False):
        op = str(node.get("range").strip())
        slot = str(node.get("slot", "").strip())

        try:
            restrict = self.op_translate[op.lstrip("r")]
        except KeyError:
            raise ValueError(f'unknown operator: {op!r}')
        if node.text is None:
            raise ValueError(f"{op!r} node missing version")

        base = str(node.text.strip())
        glob = base.endswith("*")
        if glob:
            base = base[:-1]
        base = cpv.VersionedCPV(f"cat/pkg-{base}")

        if glob:
            if op != "eq":
                raise ValueError(f"glob cannot be used with {op} ops")
            return packages.PackageRestriction(
                "fullver", values.StrGlobMatch(base.fullver))
        restrictions = []
        if op.startswith("r"):
            if not base.revision:
                if op == "rlt": # rlt -r0 can never match
                    # this is a non-range.
                    raise ValueError(
                        "range %s version %s is a guaranteed empty set" %
                        (op, str(node.text.strip())))
                elif op == "rle": # rle -r0 -> = -r0
                    return atom_restricts.VersionMatch("=", base.version, negate=negate)
                elif op == "rge": # rge -r0 -> ~
                    return atom_restricts.VersionMatch("~", base.version, negate=negate)
            # rgt -r0 passes through to regular ~ + >
            restrictions.append(atom_restricts.VersionMatch("~", base.version))
        restrictions.append(
            atom_restricts.VersionMatch(restrict, base.version, rev=base.revision),
        )
        if slot:
            restrictions.append(atom_restricts.SlotDep(slot))
        return packages.AndRestriction(*restrictions, negate=negate)





class GlsaDirError(MetadataError):
    """glsa directory parse failed."""

    ERR_NOT_EXIST = 1       # glsa directory does not exist
    ERR_INVALID = 2         # glsa directory not valid

    def __init__(self, repo, err):
        # no performance concern is needed for exception object

        assert isinstance(repo, Repo)
        assert err in [self.ERR_NOT_EXIST, self.ERR_INVALID]

        self._repo = repo
        self._err = err

    def __str__(self):
        if self._err == self.ERR_NOT_EXIST:
            return "nonexistent glsa directory %s in %s" % (_my_path, self._repo)
        elif self._err == self.ERR_INVALID:
            return "invalid glsa directory %s in %s" % (_my_path, self._repo)
        else:
            assert False


class GlsaFileError(MetadataError):

    def __init__(self, repo, err):
        # no performance concern is needed for exception object

        assert isinstance(repo, Repo)
        assert isinstance(err, str)

        self._repo = repo
        self._err = err

    def __str__(self):
        return self._err


_my_path = pjoin("metadata", "glsa")
