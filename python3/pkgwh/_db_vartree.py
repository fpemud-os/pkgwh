import os


class VarTree:

    def __init__(self, pkgwh):
        self._pkgwh = pkgwh

    def cp_list(self, category=None):                                 # FIXME: should have more advanced query parameter
        pass

    def cpv_list(self, cp_obj=None):                                  # FIXME: should have more advanced query parameter
        pass

    def package_list(self, cpv_obj=None):
        pass


class VarTreePackage:

    PROP_REPOSITORY = 10
    PROP_CATEGORY = 20

    PROP_EBUILD_FILE = 100
    PROP_EAPI = 105
    PROP_DESCRIPTION = 110
    PROP_HOMEPAGE = 115
    PROP_KEYWORDS = 120
    PROP_LICENSE = 130
    PROP_SLOT = 140
    PROP_IUSE = 150
    PROP_DEPEND = 160
    PROP_RDEPEND = 170
    PROP_BDEPEND = 180

    PROP_CHOST = 200
    PROP_CBUILD = 210
    PROP_CFLAGS = 220
    PROP_CXXFLAGS = 230
    PROP_LDFLAGS = 240
    PROP_INSTALL_MASK = 250
    PROP_ENVIRONMENT = 260

    PROP_FEATURES = 310
    PROP_IHERITED = 320
    PROP_DEFINED_PHASES = 330
    PROP_IUSE_EFFECTIVE = 340
    PROP_USE = 350

    PROP_BUILD_TIME = 400
    PROP_CONTENTS = 410
    PROP_SIZE = 420

    PROP_COUNTER = 1000             # FIXME: what is this
    PROP_REQUIRES = 1100            # FIXME: what is this
    PROP_NEEDED = 1200              # FIXME: what is this
    PROP_NEEDED_ELF = 1300          # FIXME: what is this
    PROP_PF = 1400                  # FIXME: what is this

    def __init__(self, vartree, path):
        self._pkgwh = vartree._pkgwh
        self._vartree = vartree
        self._path = path
        assert os.path.isdir(self._full_path())

    def get_cpv(self):
        assert False

    def get_property_filename(self, property_id):
        if property_id == self.PROP_REPOSITORY:
            return "repository"
        if property_id == self.PROP_CATEGORY:
            return "CATEGORY"

        if property_id == self.PROP_EBUILD_FILE:
            return os.path.basename(self._path) + ".ebuild"
        if property_id == self.PROP_EAPI:
            return "EAPI"
        if property_id == self.PROP_DESCRIPTION:
            return "DESCRIPTION"
        if property_id == self.PROP_HOMEPAGE:
            return "HOMEPAGE"
        if property_id == self.PROP_KEYWORDS:
            return "KEYWORDS"
        if property_id == self.PROP_LICENSE:
            return "LICENSE"
        if property_id == self.PROP_SLOT:
            return "SLOT"
        if property_id == self.PROP_IUSE:
            return "IUSE"
        if property_id == self.PROP_DEPEND:
            return "DEPEND"
        if property_id == self.PROP_RDEPEND:
            return "RDEPEND"
        if property_id == self.PROP_BDEPEND:
            return "BDEPEND"

        if property_id == self.PROP_CHOST:
            return "CHOST"
        if property_id == self.PROP_CBUILD:
            return "CBUILD"
        if property_id == self.PROP_CFLAGS:
            return "CFLAGS"
        if property_id == self.PROP_CXXFLAGS:
            return "CXXFLAGS"
        if property_id == self.PROP_LDFLAGS:
            return "LDFLAGS"
        if property_id == self.PROP_INSTALL_MASK:
            return "INSTALL_MASK"
        if property_id == self.PROP_ENVIRONMENT:
            return "environment.bz2"

        if property_id == self.FEATURES:
            return "FEATURES"
        if property_id == self.INHERITED:
            return "INHERITED"
        if property_id == self.PROP_DEFINED_PHASES:
            return "DEFINED_PHASES"
        if property_id == self.IUSE_EFFECTIVE:
            return "IUSE_EFFECTIVE"
        if property_id == self.PROP_USE:
            return "USE"

        if property_id == self.PROP_BUILD_TIME:
            return "BUILD_TIME"
        if property_id == self.PROP_CONTENTS:
            return "CONTENTS"
        if property_id == self.PROP_SIZE:
            return "SIZE"

        if property_id == self.PROP_COUNTER:
            return "COUNTER"
        if property_id == self.PROP_REQUIRES:
            return "REQUIRES"
        if property_id == self.NEEDED:
            return "NEEDED"
        if property_id == self.NEEDED_ELF:
            return "NEEDED.ELF.2"
        if property_id == self.PF:
            return "PF"

        assert False

    def get_property_filepath(self, property_id):
        return os.path.join(self._full_path(), self.get_property_filename(property_id))

    def get_property_data(self, property_id):
        fullfn = self.get_property_filepath(property_id)

        if property_id == self.PROP_REPOSITORY:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_CATEGORY:
            return pathlib.Path(fullfn).read_text()

        if property_id == self.PROP_EBUILD_FILE:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_EAPI:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_DESCRIPTION:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_HOMEPAGE:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_KEYWORDS:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_LICENSE:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_SLOT:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_IUSE:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_DEPEND:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_RDEPEND:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_BDEPEND:                    # non-trivial
            if os.path.exists(fullfn):
                return pathlib.Path(fullfn).read_text()
            else:
                return ""

        if property_id == self.PROP_CHOST:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_CBUILD:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_CFLAGS:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_CXXFLAGS:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_LDFLAGS:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_INSTALL_MASK:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_ENVIRONMENT:                # non-trivial
            with bz2.open(fullfn, "r") as f:
                return f.read()

        if property_id == self.FEATURES:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.INHERITED:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_DEFINED_PHASES:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.IUSE_EFFECTIVE:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_USE:
            return pathlib.Path(fullfn).read_text()

        if property_id == self.PROP_BUILD_TIME:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.PROP_CONTENTS:                                     # FIXME: return EntrySet
            return None
        if property_id == self.PROP_SIZE:                       # non-trivial
            return int(pathlib.Path(fullfn).read_text())

        if property_id == self.PROP_COUNTER:                    # non-trivial
            return int(pathlib.Path(fullfn).read_text())
        if property_id == self.PROP_REQUIRES:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.NEEDED:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.NEEDED_ELF:                                         # FIXME: ?? 
            return None
        if property_id == self.PF:
            return pathlib.Path(fullfn).read_text()

        assert False

    def _full_path(self):
        return os.path.join(self._pkgwh.config.pkg_db_dir, self._path)


class VarTreeWriter:

    def __init__(self, pkgwh):
        self._pkgwh = pkgwh

    def add_pkg(self, cpv):
        pass

    def remove_pkg(self, cpv):
        pass

    def replace_pkg(self, cpv):
        pass
