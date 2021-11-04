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


from abc import ABC
from enum import Enum, auto


class VarTreePackageProperty(Enum):

    REPOSITORY = auto()
    CATEGORY = auto()

    EBUILD_FILE = auto()                # ebuild file content
    EAPI = auto()
    DESCRIPTION = auto()
    HOMEPAGE = auto()
    KEYWORDS = auto()
    LICENSE = auto()
    SLOT = auto()
    IUSE = auto()
    DEPEND = auto()
    RDEPEND = auto()
    BDEPEND = auto()

    CHOST = auto()
    CBUILD = auto()
    CFLAGS = auto()
    CXXFLAGS = auto()
    LDFLAGS = auto()
    INSTALL_MASK = auto()
    ENVIRONMENT = auto()

    FEATURES = auto()
    IHERITED = auto()
    DEFINED_PHASES = auto()
    IUSE_EFFECTIVE = auto()
    USE = auto()

    BUILD_TIME = auto()
    CONTENTS = auto()
    SIZE = auto()

    COUNTER = auto()             # FIXME: what is this
    REQUIRES = auto()            # FIXME: what is this
    NEEDED = auto()              # FIXME: what is this
    NEEDED_ELF = auto()          # FIXME: what is this
    PF = auto()                  # FIXME: what is this


class VarTreeBase(ABC):

    def cp_list(self, category=None):                                 # FIXME: should have more advanced query parameter
        raise NotImplementedError()

    def cpv_list(self, cp_obj=None):                                  # FIXME: should have more advanced query parameter
        raise NotImplementedError()

    def package_list(self, cpv_obj=None):
        raise NotImplementedError()


class VarTreeRwBase(ABC):

    @property
    def vartree(self):
        raise NotImplementedError()

    def cp_list(self, category=None):                                 # FIXME: should have more advanced query parameter
        raise NotImplementedError()

    def cpv_list(self, cp_obj=None):                                  # FIXME: should have more advanced query parameter
        raise NotImplementedError()

    def package_list(self, cpv_obj=None):
        raise NotImplementedError()

    def add_package(self, cpv):
        raise NotImplementedError()

    def remove_package(self, cpv):
        raise NotImplementedError()

    def replace_package(self, cpv):
        raise NotImplementedError()


class VarTreePackageBase(ABC):

    def get_cpv(self):
        raise NotImplementedError()

    def get_property_data(self, property_id : VarTreePackageProperty):
        raise NotImplementedError()
