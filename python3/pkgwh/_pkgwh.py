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
import glob
import robust_layer.simple_fops

from ._po import BootMode
from ._po import KernelType
from ._po import RescueOsSpec
from ._config import EtcDirConfig
from ._exception import RunningEnvironmentError

from ._util import Util
from ._po import FsLayout
from ._check import Checker


class Pkgwh:

    def __init__(self, cfg=EtcDirConfig()):
        self._cfg = cfg

        if self._cfg.get_kernel_type() == KernelType.LINUX:
            self._fsLayout = FsLayout(self)
        else:
            assert False

        self._repoList = [
            Repo(self, self._cfg.data_repo_dir),
        ]

    @property
    def config(self):
        return self._cfg

    @property
    def repositories(self):
        return self._repoList

    def check_running_environment(self):
        if not os.path.isdir(self._fsLayout.get_boot_dir()):
            raise RunningEnvironmentError("directory \"%s\" does not exist" % (self._fsLayout.get_boot_dir()))
        if not os.path.isdir(self._fsLayout.get_lib_dir()):
            raise RunningEnvironmentError("directory \"%s\" does not exist" % (self._fsLayout.get_lib_dir()))

        if not Util.cmdCallTestSuccess("make", "-v"):
            raise RunningEnvironmentError("executable \"make\" does not exist")

        if not Util.cmdCallTestSuccess("grub-script-check", "-V"):
            raise RunningEnvironmentError("executable \"grub-script-check\" does not exist")
        if not Util.cmdCallTestSuccess("grub-editenv", "-V"):
            raise RunningEnvironmentError("executable \"grub-editenv\" does not exist")
        if not Util.cmdCallTestSuccess("grub-install", "-V"):
            raise RunningEnvironmentError("executable \"grub-install\" does not exist")

    def get_package_tree(self):
        raise NotImplementedError()

    def get_installed_package_tree(self):
        raise NotImplementedError()

    def install_package(self, package_atom):
        pass

    def clean_packages(self, pretend=False):
        # # return value
        # return (bootFileList, modulesFileList, firmwareFileList)
        pass

    def clean_distfiles(self, pretend=False):
        return []                               # FIXME

    def check_config(self, autofix=False, error_callback=None):
        pass

    def check_repositories(self, autofix=False, error_callback=None):
        pass

    def check_packages(self, autofix=False, error_callback=None):
        pass