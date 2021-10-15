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
from ._util import Util
from ._exception import RunningEnvironmentError


class RepoPriority:

    MAX = 9999
    CORE = 9000
    ADDON_OFFICIAL = 8000
    ADDON_UNOFFICIAL = 7000
    MIN = 0


class RepoSyncInfo:

    TYPE_RSYNC = 1
    TYPE_GIT = 2
    TYPE_SUBVERSION = 3

    def __init__(self, name):
        self.name = name


class RepoSyncInfoRsync(RepoSyncInfo):

    def __init__(self, url):
        assert url.startswith("rsync://")
        super().__init__(RepoSyncInfo.TYPE_RSYNC)
        self.url = url


class RepoSyncInfoGit(RepoSyncInfo):

    def __init__(self, url):
        assert url.startswith("git://") or url.startswith("http://") or url.startswith("https://")
        super().__init__(RepoSyncInfo.TYPE_GIT)
        self.url = url


class RepoSyncInfoSubversion(RepoSyncInfo):

    def __init__(self, url):
        assert url.startswith("http://") or url.startswith("https://")
        super().__init__(RepoSyncInfo.TYPE_SUBVERSION)
        self.url = url
