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
import re
import configparser
from ._util import Util
from ._exception import ConfigError


class Config:

    @property
    def cfg_repo_dir(self):
        raise NotImplementedError()

    @property
    def cfg_repo_patch_dir(self):
        raise NotImplementedError()

    @property
    def data_repo_dir(self):
        raise NotImplementedError()

    @property
    def data_world_file(self):
        raise NotImplementedError()

    @property
    def cache_repo_dir(self):
        raise NotImplementedError()

    @property
    def cache_distfiles_dir(self):
        raise NotImplementedError()

    @property
    def cache_distfiles_ro_dir_list(self):
        raise NotImplementedError()

    @property
    def pkg_db_dir(self):
        raise NotImplementedError()

    @property
    def tmp_dir(self):
        raise NotImplementedError()

    def get_build_variable(self, var_name):
        raise NotImplementedError()

    def is_package_masked(self, package_atom):
        raise NotImplementedError()

    def do_check(self, pkgwh, autofix, error_callback):
        raise NotImplementedError()


class EtcDirConfig(Config):

    DEFAULT_CONFIG_DIR = "/etc/portage"

    DEFAULT_DATA_DIR = "/var/lib/portage"

    DEFAULT_CACHE_DIR = "/var/cache/portage"

    DEFAULT_PKGDB_DIR = "/var/db/pkg"

    DEFAULT_TMP_DIR = "/var/tmp/portage"

    def __init__(self, cfgdir=DEFAULT_CONFIG_DIR):
        self._makeConf = os.path.join(cfgdir, "make.conf")

        self._profileDir = os.path.join(cfgdir, "make.profile")

        self._cfgRepoDir = os.path.join(cfgdir, "repos.conf")
        self._cfgRepoPatchDir = os.path.join(cfgdir, "repos.patch")

        self._cfgAcceptKeywordsDir = os.path.join(cfgdir, "package.accept_keywords")
        self._cfgMaskDir = os.path.join(cfgdir, "package.mask")
        self._cfgUseDir = os.path.join(cfgdir, "package.use")
        self._cfgLicDir = os.path.join(cfgdir, "package.license")
        self._cfgEnvDir = os.path.join(cfgdir, "package.env")

        self._dataDir = self.DEFAULT_DATA_DIR
        self._dataReposDir = os.path.join(self._dataDir, "repos")
        self._dataWordFile = os.path.join(self._dataDir, "world")

        self._cacheDir = self.DEFAULT_CACHE_DIR
        self._cacheReposDir = os.path.join(self._cacheDir, "repos")
        self._cacheDistfilesDir = os.path.join(self._cacheDir, "distfiles")
        self._cacheDistfilesRoDirList = []

        self._pkgDbDir = self.DEFAULT_PKGDB_DIR

        self._tmpDir = self.DEFAULT_TMP_DIR

        self._deparecateCfgUnmaskDir = os.path.join(cfgdir, "package.unmask")
        self._deprecateCfgEnvDataDir = os.path.join(cfgdir, "env")
        self._deprecateCfgMirrorsFile = os.path.join(cfgdir, "mirrors")

    @property
    def cfg_repo_dir(self):
        return self._cfgRepoDir

    @property
    def cfg_repo_patch_dir(self):
        return self._cfgRepoPatchDir

    @property
    def data_repo_dir(self):
        return self._dataRepoDir

    @property
    def data_world_file(self):
        return self._dataWordFile

    @property
    def cache_repo_dir(self):
        return self._cacheRepoDir

    @property
    def cache_distfiles_dir(self):
        return self._cacheDistfilesDir

    @property
    def cache_distfiles_ro_dir_list(self):
        return self._cacheDistfilesRoDirList

    @property
    def pkg_db_dir(self):
        return self._pkgDbDir

    @property
    def tmp_dir(self):
        return self._tmpDir

    def get_build_variable(self, var_name):
        return self._getMakeConfVariable(var_name)

    def is_package_masked(self, package_atom):
        return True

    def do_check(self, pkgwh, autofix, error_callback):
        raise NotImplementedError()

    def _getMakeConfVariable(self, varName):
        # Returns variable value, returns "" when not found
        # Multiline variable definition is not supported yet

        buf = ""
        with open(self._makeConf, 'r') as f:
            buf = f.read()

        m = re.search("^%s=\"(.*)\"$" % varName, buf, re.MULTILINE)
        if m is None:
            return ""
        varVal = m.group(1)

        while True:
            m = re.search("\\${(\\S+)?}", varVal)
            if m is None:
                break
            varName2 = m.group(1)
            varVal2 = self._getMakeConfVariable(self._makeConf, varName2)
            if varVal2 is None:
                varVal2 = ""

            varVal = varVal.replace(m.group(0), varVal2)

        return varVal
