#!/usr/bin/env python3

# Copyright (c) 2005-2014 Fpemud <fpemud@sina.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


import os
import pathlib
from ._db_vartree import VarTreeBase, VarTreeRwBase, VarTreePackageBase, VarTreePackageProperty


class VarTree(VarTreeBase):

    def __init__(self, vartree_rw):
        self._rw = vartree_rw

    @property
    def path(self):
        return self._rw.path

    def cp_list(self, category=None):                                 # FIXME: should have more advanced query parameter
        self._rw.cp_list()

    def cpv_list(self, cp_obj=None):                                  # FIXME: should have more advanced query parameter
        self._rw.cpv_list()

    def package_list(self, cpv_obj=None):
        self._rw.package_list()


class VarTreeRw(VarTreeRwBase):

    def __init__(self, pkgwh):
        self._pkgwh = pkgwh

    @property
    def path(self):
        return "/var/db/pkg"

    def cp_list(self, category=None):                                 # FIXME: should have more advanced query parameter
        assert False

    def cpv_list(self, cp_obj=None):                                  # FIXME: should have more advanced query parameter
        assert False

    def package_list(self, cpv_obj=None):
        assert False

    def add_package(self, cpv):
        raise NotImplementedError()

    def remove_package(self, cpv):
        raise NotImplementedError()

    def replace_package(self, cpv):
        raise NotImplementedError()


class VarTreePackage(VarTreePackageBase):

    def __init__(self, vartree_rw, path):
        self._rw = vartree_rw
        self._path = path
        assert os.path.isdir(self._full_path())

    def get_cpv(self):
        assert False

    def get_property_filename(self, property_id : VarTreePackageProperty):
        if property_id == VarTreePackageProperty.REPOSITORY:
            return "repository"
        if property_id == VarTreePackageProperty.CATEGORY:
            return "CATEGORY"

        if property_id == VarTreePackageProperty.EBUILD_FILE:
            return os.path.basename(self._path) + ".ebuild"
        if property_id == VarTreePackageProperty.EAPI:
            return "EAPI"
        if property_id == VarTreePackageProperty.DESCRIPTION:
            return "DESCRIPTION"
        if property_id == VarTreePackageProperty.HOMEPAGE:
            return "HOMEPAGE"
        if property_id == VarTreePackageProperty.KEYWORDS:
            return "KEYWORDS"
        if property_id == VarTreePackageProperty.LICENSE:
            return "LICENSE"
        if property_id == VarTreePackageProperty.SLOT:
            return "SLOT"
        if property_id == VarTreePackageProperty.IUSE:
            return "IUSE"
        if property_id == VarTreePackageProperty.DEPEND:
            return "DEPEND"
        if property_id == VarTreePackageProperty.RDEPEND:
            return "RDEPEND"
        if property_id == VarTreePackageProperty.BDEPEND:
            return "BDEPEND"

        if property_id == VarTreePackageProperty.CHOST:
            return "CHOST"
        if property_id == VarTreePackageProperty.CBUILD:
            return "CBUILD"
        if property_id == VarTreePackageProperty.CFLAGS:
            return "CFLAGS"
        if property_id == VarTreePackageProperty.CXXFLAGS:
            return "CXXFLAGS"
        if property_id == VarTreePackageProperty.LDFLAGS:
            return "LDFLAGS"
        if property_id == VarTreePackageProperty.INSTALL_MASK:
            return "INSTALL_MASK"
        if property_id == VarTreePackageProperty.ENVIRONMENT:
            return "environment.bz2"

        if property_id == self.FEATURES:
            return "FEATURES"
        if property_id == self.INHERITED:
            return "INHERITED"
        if property_id == VarTreePackageProperty.DEFINED_PHASES:
            return "DEFINED_PHASES"
        if property_id == self.IUSE_EFFECTIVE:
            return "IUSE_EFFECTIVE"
        if property_id == VarTreePackageProperty.USE:
            return "USE"

        if property_id == VarTreePackageProperty.BUILD_TIME:
            return "BUILD_TIME"
        if property_id == VarTreePackageProperty.CONTENTS:
            return "CONTENTS"
        if property_id == VarTreePackageProperty.SIZE:
            return "SIZE"

        if property_id == VarTreePackageProperty.COUNTER:
            return "COUNTER"
        if property_id == VarTreePackageProperty.REQUIRES:
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

        if property_id == VarTreePackageProperty.REPOSITORY:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.CATEGORY:
            return pathlib.Path(fullfn).read_text()

        if property_id == VarTreePackageProperty.EBUILD_FILE:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.EAPI:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.DESCRIPTION:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.HOMEPAGE:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.KEYWORDS:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.LICENSE:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.SLOT:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.IUSE:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.DEPEND:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.RDEPEND:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.BDEPEND:                    # non-trivial
            if os.path.exists(fullfn):
                return pathlib.Path(fullfn).read_text()
            else:
                return ""

        if property_id == VarTreePackageProperty.CHOST:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.CBUILD:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.CFLAGS:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.CXXFLAGS:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.LDFLAGS:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.INSTALL_MASK:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.ENVIRONMENT:                # non-trivial
            with bz2.open(fullfn, "r") as f:
                return f.read()

        if property_id == self.FEATURES:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.INHERITED:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.DEFINED_PHASES:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.IUSE_EFFECTIVE:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.USE:
            return pathlib.Path(fullfn).read_text()

        if property_id == VarTreePackageProperty.BUILD_TIME:
            return pathlib.Path(fullfn).read_text()
        if property_id == VarTreePackageProperty.CONTENTS:                                     # FIXME: return EntrySet
            return None
        if property_id == VarTreePackageProperty.SIZE:                       # non-trivial
            return int(pathlib.Path(fullfn).read_text())

        if property_id == VarTreePackageProperty.COUNTER:                    # non-trivial
            return int(pathlib.Path(fullfn).read_text())
        if property_id == VarTreePackageProperty.REQUIRES:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.NEEDED:
            return pathlib.Path(fullfn).read_text()
        if property_id == self.NEEDED_ELF:                                         # FIXME: ?? 
            return None
        if property_id == self.PF:
            return pathlib.Path(fullfn).read_text()

        assert False

    def _full_path(self):
        return os.path.join(self._rw.path, self._path)
