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
import robust_layer.simple_fops
from ._util import Util
from ._boot_entry import BootEntryUtils
from ._boot_entry import BootEntryWrapper
from ._bootloader import BootLoader


class Checker:

    def __init__(self, pkgwh, auto_fix=False, error_callback=None):
        self._pkgwh = pkgwh
        self._bAutoFix = auto_fix
        self._errCb = error_callback if error_callback is not None else self._doNothing

    def checkRepository(self, repo):
        # check existence
        if not repo.exists:
            if bAutoFix:
                self.createRepository(self._repoName)
            else:
                raise RepositoryCheckError("repository \"%s\" does not exist" % (self._repoName))

        cfgFile = self.getRepoCfgReposFile(self._repoName)
        repoDir = self.getRepoDir(self._repoName)

        # check cfgFile content
        if True:
            standardContent = self.__generateReposConfContent(self._repoName)
            if pathlib.Path(cfgFile).read_text() != standardContent:
                if bAutoFix:
                    with open(cfgFile, "w") as f:
                        f.write(standardContent)
                else:
                    raise RepositoryCheckError("file content of \"%s\" is invalid" % (cfgFile))

        # check repository directory existence
        if not os.path.exists(repoDir):
            if bAutoFix:
                self.createRepository(self._repoName)
            else:
                raise RepositoryCheckError("repository directory \"%s\" does not exist" % (repoDir))

        # check repository directory validity
        if not os.path.isdir(repoDir):
            if bAutoFix:
                robust_layer.simple_fops.rm(repoDir)
                self.createRepository(self._repoName)
            else:
                raise RepositoryCheckError("repository directory \"%s\" is invalid" % (repoDir))

        # check repository source url
        if self._repoName in self._repoGitUrlDict and FmUtil.gitGetUrl(repoDir) != self._repoGitUrlDict[self._repoName]:
            if bAutoFix:
                robust_layer.simple_fops.rm(repoDir)
                self.createRepository(self._repoName)
            else:
                raise RepositoryCheckError("repository directory \"%s\" should have URL \"%s\"" % (repoDir, self._repoGitUrlDict[self._repoName]))




    def _doNothing(self, msg):
        pass
