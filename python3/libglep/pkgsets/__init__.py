
class SystemSet:
    """Set of system packages defined by the selected profile."""

    def __iter__(self):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()

    def __contains__(self, key):
        raise NotImplementedError()


class WorldSet:
    """Set of packages contained in the world file."""

    def add(self, cp):
        raise NotImplementedError()

    def remove(self, cp):
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

    def __len__(self):
        raise NotImplementedError()

    def __contains__(self, key):
        raise NotImplementedError()


class GlsaDirSet(metaclass=generic_equality):
    """Pkgset based on GLSA's distributed via a directory."""

    pkgcore_config_type = ConfigHint({'src': 'ref:repo'}, typename='pkgset')
    op_translate = {"ge": ">=", "gt": ">", "lt": "<", "le": "<=", "eq": "="}
    __attr_comparison__ = ('paths',)

    def __init__(self, src):
        """
        :param src: where to get the glsa from
        :type src: must be either full path to glsa dir, or a repo object to pull it from

        Currently we only supports one glsa directory.
        """

        if not isinstance(src, str):
            src = tuple(sorted(
                filter(os.path.isdir, (pjoin(
                    repo.base, 'metadata', 'glsa') for repo in
                    get_virtual_repos(src, False) if hasattr(repo, 'base'))
                )))
        else:
            src = [src]
        self.paths = src

    def __iter__(self):
        for glsa, catpkg, pkgatom, vuln in self.iter_vulnerabilities():
            yield packages.KeyedAndRestriction(
                pkgatom, vuln, key=catpkg, tag="GLSA vulnerable:")

    def pkg_grouped_iter(self, sorter=None):
        """yield GLSA restrictions grouped by package key

        :param sorter: must be either None, or a comparison function
        """

        if sorter is None:
            sorter = iter
        pkgs = {}
        pkgatoms = {}
        for glsa, pkg, pkgatom, vuln in self.iter_vulnerabilities():
            pkgatoms[pkg] = pkgatom
            pkgs.setdefault(pkg, []).append(vuln)

        for pkgname in sorter(pkgs):
            yield packages.KeyedAndRestriction(
                pkgatoms[pkgname], packages.OrRestriction(*pkgs[pkgname]), key=pkgname)

    def iter_vulnerabilities(self):
        """generator yielding each GLSA restriction"""
        for path in self.paths:
            for fn in listdir_files(path):
                # glsa-1234-12.xml
                if not (fn.startswith("glsa-") and fn.endswith(".xml")):
                    logger.warning(f'invalid glsa file name: {fn!r}')
                    continue
                # This verifies the filename is of the correct syntax.
                try:
                    [int(x) for x in fn[5:-4].split("-")]
                except ValueError:
                    logger.warning(f'invalid glsa file name: {fn!r}')
                    continue
                root = etree.parse(pjoin(path, fn))
                glsa_node = root.getroot()
                if glsa_node.tag != 'glsa':
                    logger.warning(f'glsa file without glsa root node: {fn!r}')
                    continue
                for affected in root.findall('affected'):
                    for pkg in affected.findall('package'):
                        try:
                            pkgname = str(pkg.get('name')).strip()
                            pkg_vuln_restrict = \
                                self.generate_intersects_from_pkg_node(
                                    pkg, tag="glsa(%s)" % fn[5:-4])
                            if pkg_vuln_restrict is None:
                                continue
                            pkgatom = atom.atom(pkgname)
                            yield fn[5:-4], pkgname, pkgatom, pkg_vuln_restrict
                        except (TypeError, ValueError) as e:
                            # thrown from cpv.
                            logger.warning(f"invalid glsa file {fn!r}, package {pkgname}: {e}")
                        except IGNORED_EXCEPTIONS:
                            raise
                        except Exception as e:
                            logger.warning(f"invalid glsa file {fn!r}: {e}")

    def generate_intersects_from_pkg_node(self, pkg_node, tag=None):
        arch = pkg_node.get("arch")
        if arch is not None:
            arch = tuple(str(arch.strip()).split())
            if not arch or "*" in arch:
                arch = None

        vuln = list(pkg_node.findall("vulnerable"))
        if not vuln:
            return None
        elif len(vuln) > 1:
            vuln_list = [self.generate_restrict_from_range(x) for x in vuln]
            vuln = packages.OrRestriction(*vuln_list)
        else:
            vuln_list = [self.generate_restrict_from_range(vuln[0])]
            vuln = vuln_list[0]
        if arch is not None:
            vuln = packages.AndRestriction(vuln, packages.PackageRestriction(
                "keywords", values.ContainmentMatch2(arch, match_all=False)))
        invuln = (pkg_node.findall("unaffected"))
        if not invuln:
            # wrap it.
            return packages.KeyedAndRestriction(vuln, tag=tag)
        invuln_list = [self.generate_restrict_from_range(x, negate=True)
                       for x in invuln]
        invuln = [x for x in invuln_list if x not in vuln_list]
        if not invuln:
            if tag is None:
                return packages.KeyedAndRestriction(vuln, tag=tag)
            return packages.KeyedAndRestriction(vuln, tag=tag)
        return packages.KeyedAndRestriction(vuln, tag=tag, *invuln)

    def generate_restrict_from_range(self, node, negate=False):
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
