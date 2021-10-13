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
import pathlib
import robust_layer.simple_git
import robust_layer.simple_fops


class Repo:

    PRIORITY_MAX = 9999
    PRIORITY_CORE = 9000
    PRIORITY_ADDON_OFFICIAL = 8000
    PRIORITY_ADDON_UNOFFICIAL = 7000
    PRIORITY_MIN = 0

    def __init__(self, pkgwh, name):
        self._pkgwh = pkgwh
        self._repoName = name

        self._priority = None
        self._syncInfo = None
        self._usingFilesDir = None
        self._innerRepoName = None
        self._hideList = None
        self._unhideList = None
        self._patchDirList = None
        self._invalidReason = None
        self._parse()

    def exists(self):
        return os.path.exists(self.repo_conf_file())

    def exists_and_valid(self):
        return self.exists() and self._invalidReason is None

    @property
    def repo_conf_file(self):
        assert self.exists_and_valid()
        return _repoConfFile(self._pkgwh, self._repoName)

    @property
    def repo_dir(self):
        assert self.exists_and_valid()
        return _repoDir(self._pkgwh, self._repoName)

    @property
    def priority(self):
        assert self.exists_and_valid()
        return self._priority

    @property
    def sync_info(self):
        assert self.exists_and_valid()
        return self._syncInfo

    def get_metadata(self, key):
        # meta-data:
        #   1. repo-name: XXXX
        assert self.exists_and_valid()

        if key == "repo-name":
            return self._innerRepoName
        else:
            assert False

    def get_invalid_reason(self):
        assert not self.exists_and_valid()
        return self._invalidReason

    def create(self, priority=None, sync_type=None, sync_info=None):
        # Business exception should not be raise, but be printed as error message
        assert priority is None or (self.PRIORITY_MAX >= priority >= self.PRIORITY_MIN)
        assert sync_type is None or sync_info is None
        assert not self.exists()

        buf = self._generateCfgReposFileContent()       # may raise exception
        with open(self.repo_conf_file, "w") as f:
            f.write(buf)

        self.sync()

    def sync(self):
        # Business exception should not be raise, but be printed as error message
        assert self.exists()

        if self._syncInfo is None:
            robust_layer.simple_fops.mkdir(self.repo_dir)
        elif self._syncInfo.name == RepoSyncInfo.RSYNC:
            _RepoSyncRsync.sync(self)
        elif self._syncInfo.name == RepoSyncInfo.GIT:
            _RepoSyncGit.sync(self)
        elif self._syncInfo.name == RepoSyncInfo.SUBVERSION:
            _RepoSyncSubversion.sync(self)
        else:
            assert False








        if self.__hasPatch(self._repoName):
            print("Patching...")
            self.__patchRepoN(self._repoName)
            self.__patchRepoS(self._repoName)
            print("Done.")


    def _parse(self, buf):
        if not os.path.exists(self.repo_conf_file()):
            return

        buf = pathlib.Path(self.repo_conf_file).read_text()
        lineList = buf.split("\n")
        try:
            # innerRepoName
            m = re.search("^\\[(.*)\\]$", buf, re.M)
            if m is not None:
                innerRepoName = m.group(1)
            else:
                raise _InternalParseError("invalid repos.conf file")

            # priority
            m = re.search("^priority *= *(.*)$", buf, re.M)
            if m is not None:
                try:
                    priority = int(m.group(1))
                except ValueError:
                    raise _InternalParseError("invalid \"priority\" in repos.conf file")
                if not (self.PRIORITY_MAX >= priority >= self.PRIORITY_MIN):
                    raise _InternalParseError("invalid \"priority\" in repos.conf file")
            else:
                raise _InternalParseError("no \"priority\" in repos.conf file")

            # location
            m = re.search("^location *= *(.*)$", buf, re.M)
            if m is not None:
                location = m.group(1)
                if location != self.repo_dir:
                    raise _InternalParseError("invalid \"location\" in repos.conf file")
            else:
                raise _InternalParseError("no \"location\" in repos.conf file")

            # syncInfo
            if True:
                m = re.search("^sync-type *= *(.*)$", buf, re.M)
                if m is not None:
                    vcsType = m.group(1)
                else:
                    vcsType = None

                m = re.search("^sync-uri *= *(.*)$", buf, re.M)
                if m is not None:
                    overlayUrl = m.group(1)
                else:
                    overlayUrl = None

                if vcsType is None:
                    syncInfo = None
                elif vcsType == RepoSyncInfo.RSYNC:
                    if not overlayUrl.startswith("rsync://"):
                        raise _InternalParseError("invalid \"sync-url\" in repos.conf file")
                    syncInfo = RepoSyncInfoRsync(overlayUrl)
                elif vcsType == RepoSyncInfo.GIT:
                    if not (overlayUrl.startswith("git://") or overlayUrl.startswith("http://") or overlayUrl.startswith("https://")):
                        raise _InternalParseError("invalid \"sync-url\" in repos.conf file")
                    syncInfo = RepoSyncInfoGit(overlayUrl)
                elif vcsType == RepoSyncInfo.SUBVERSION:
                    if not (overlayUrl.startswith("http://") or overlayUrl.startswith("https://")):
                        raise _InternalParseError("invalid \"sync-url\" in repos.conf file")
                    syncInfo = RepoSyncInfoGit(overlayUrl)
                else:
                    raise _InternalParseError("invalid \"sync-type\" in repos.conf file")

            # hideList
            hideList = None
            for line in lineList:
                if hideList is not None:
                    if re.fullmatch("\\[package.hide\\]", line) is not None:
                        hideList = []
                else:
                    if re.fullmatch("\\[(.*)\\]", line) is not None:
                        break
                    hideList.append(line.strip())
            if hideList is None:
                hideList = []

            # unhideList
            unhideList = None
            for line in lineList:
                if unhideList is not None:
                    if re.fullmatch("\\[package.unhide\\]", line) is not None:
                        unhideList = []
                else:
                    if re.fullmatch("\\[(.*)\\]", line) is not None:
                        break
                    unhideList.append(line.strip())
            if unhideList is None:
                unhideList = []

            # check repoDir
            repoDir = _repoDir(self._pkgwh, self._repoName)
            if not os.path.isdir(repoDir):
                raise _InternalParseError("\"%s\" does not exist or invalid" % (repoDir))

            self._prioriry = priority
            self._syncInfo = syncInfo
            self._innerRepoName = innerRepoName
            self._hideList = hideList
            self._unhideList = unhideList
            self._invalidReason = None
        except _InternalParseError as e:
            self._prioriry = None
            self._syncInfo = None
            self._innerRepoName = None
            self._hideList = None
            self._unhideList = None
            self._invalidReason = e.message

    def _generateCfgReposFileContent(self):
        buf = ""
        buf += "[%s]\n" % (self._innerRepoName)
        buf += "priority = %s\n" % (self._priority)
        buf += "location = %s\n" % (self.repo_dir)
        if self._syncInfo is None:
            pass
        elif self._syncInfo.name == RepoSyncInfo.RSYNC:
            buf += "sync-type = rsync\n"
            buf += "sync-uri = %s\n" % (self._syncInfo.url)
        elif self._syncInfo.name == RepoSyncInfo.GIT:
            buf += "sync-type = rsync\n"
            buf += "sync-uri = %s\n" % (self._syncInfo.url)
        elif self._syncInfo.name == RepoSyncInfo.SUBVERSION:
            buf += "sync-type = rsync\n"
            buf += "sync-uri = %s\n" % (self._syncInfo.url)
        else:
            assert False
        return buf


class RepoSyncInfo:

    RSYNC = 1
    GIT = 2
    SUBVERSION = 3

    def __init__(self, name):
        self.name = name


class RepoSyncInfoRsync(RepoSyncInfo):

    def __init__(self, url):
        assert url.startswith("rsync://")
        super().__init__(RepoSyncInfo.RSYNC)
        self.url = url


class RepoSyncInfoGit(RepoSyncInfo):

    def __init__(self, url):
        assert url.startswith("git://") or url.startswith("http://") or url.startswith("https://")
        super().__init__(RepoSyncInfo.GIT)
        self.url = url


class RepoSyncInfoGit(RepoSyncInfo):

    def __init__(self, url):
        assert url.startswith("http://") or url.startswith("https://")
        super().__init__(RepoSyncInfo.SUBVERSION)
        self.url = url


class _RepoSyncRsync:

    @staticmethod
    def sync(repo):
        # we use "-rlptD" insead of "-a" so that the remote user/group is ignored
        robust_layer.rsync.exec("-rlptD", "-z", "-hhh", "--no-motd", "--delete", "--info=progress2", repo.sync_info.url, repo.repo_dir)


class _RepoSyncGit:

    @staticmethod
    def sync(repo):
        robust_layer.simple_git.pull(repo.repo_dir, reclone_on_failure=True, url=repo.sync_info.url)


class _RepoSyncSubversion:

    @staticmethod
    def sync(repo):
        assert False




class RepoCreator:

    def __init__(self, pkgwh):
        self._pkgwh = pkgwh

    def create_new_repo(name, priority, syncInfo, usingFilesDir):
        pass

    def _generateCfgReposFile(self):
        buf = ""
        buf += "[%s]\n" % (self._innerRepoName)
        buf += "priority = %s\n" % (self._priority)
        buf += "location = %s\n" % (self.repo_dir)
        if self._syncInfo is None:
            pass
        elif self._syncInfo.name == RepoSyncInfo.RSYNC:
            buf += "sync-type = rsync\n"
            buf += "sync-uri = %s\n" % (self._syncInfo.url)
        elif self._syncInfo.name == RepoSyncInfo.GIT:
            buf += "sync-type = rsync\n"
            buf += "sync-uri = %s\n" % (self._syncInfo.url)
        elif self._syncInfo.name == RepoSyncInfo.SUBVERSION:
            buf += "sync-type = rsync\n"
            buf += "sync-uri = %s\n" % (self._syncInfo.url)
        else:
            assert False

        with open(self.repo_conf_file, "w") as f:
            f.write(buf)


class _InternalParseError(Exception):
    pass


def _repoConfFile(pkgwh, repoName):
    # returns /etc/portage/repos.conf/XXXX.conf
    return os.path.join(pkgwh.config.repos_dir, "%s.conf" % (repoName))


def _repoDir(pkgwh, repoName):
    # returns /var/lib/portage/repos/XXXX
    return os.path.join(pkgwh.config.data_repo_dir, "%s" % (repoName))


def _repoFilesDir(pkgwh, repoName):
    # returns /var/cache/portage/repos/XXXX
    return os.path.join(pkgwh.config.cache_repo_dir, "%s" % (repoName))
















    def createRepository(self, self._repoName):
        """Business exception should not be raise, but be printed as error message"""

        if self._repoName == "gentoo":
            self._repoGentooCreate(self.getRepoDir("gentoo"))
        else:
            if self._repoName in self._repoGitUrlDict:
                robust_layer.simple_git.pull(self.getRepoDir(self._repoName), reclone_on_failure=True, url=self._repoGitUrlDict[self._repoName])
            else:
                assert False

        if self.__hasPatch(self._repoName):
            print("Patching...")
            self.__patchRepoN(self._repoName)
            self.__patchRepoS(self._repoName)
            print("Done.")

        with open(self.getRepoCfgReposFile(self._repoName), "w") as f:
            f.write(self.__generateReposConfContent(self._repoName))

    def syncRepository(self, self._repoName):
        """Business exception should not be raise, but be printed as error message"""

        if self._repoName == "gentoo":
            self._repoGentooSync(self.getRepoDir("gentoo"))
        else:
            if self._repoName in self._repoGitUrlDict:
                robust_layer.simple_git.pull(self.getRepoDir(self._repoName), reclone_on_failure=True, url=self._repoGitUrlDict[self._repoName])
            else:
                assert False

        if self.__hasPatch(self._repoName):
            print("Patching...")
            self.__patchRepoN(self._repoName)
            self.__patchRepoS(self._repoName)
            print("Done.")

    def _repoGentooCreate(self, repoDir):
        os.makedirs(repoDir, exist_ok=True)
        self._repoGentooSync(repoDir)

    def _repoGentooSync(self, repoDir):
        mr = FmUtil.portageGetGentooPortageRsyncMirror(FmConst.portageCfgMakeConf, FmConst.defaultRsyncMirror)
        robust_layer.rsync.exec("-rlptD", "-z", "-hhh", "--no-motd", "--delete", "--info=progress2", mr, repoDir)   # we use "-rlptD" insead of "-a" so that the remote user/group is ignored

    def __generateReposConfContent(self, self._repoName):
        repoDir = self.getRepoDir(self._repoName)
        buf = ""
        buf += "[%s]\n" % (FmUtil.repoGetRepoName(repoDir))
        buf += "auto-sync = no\n"
        buf += "priority = %d\n" % (self._repoInfoDict[self._repoName])
        buf += "location = %s\n" % (repoDir)
        return buf

    def __hasPatch(self, self._repoName):
        repoName2 = "repo-%s" % (self._repoName)
        for dirName in ["pkgwh-n-patch", "pkgwh-s-patch"]:
            modDir = os.path.join(FmConst.dataDir, dirName, repoName2)
            if os.path.exists(modDir):
                return True
        return False

    def __patchRepoN(self, self._repoName):
        repoName2 = "repo-%s" % (self._repoName)
        modDir = os.path.join(FmConst.dataDir, "pkgwh-n-patch", repoName2)
        if os.path.exists(modDir):
            jobCount = FmUtil.portageGetJobCount(FmConst.portageCfgMakeConf)
            FmUtil.portagePatchRepository(repoName2, self.getRepoDir(self._repoName), "N-patch", modDir, jobCount)

    def __patchRepoS(self, self._repoName):
        repoName2 = "repo-%s" % (self._repoName)
        modDir = os.path.join(FmConst.dataDir, "pkgwh-s-patch", repoName2)
        if os.path.exists(modDir):
            jobCount = FmUtil.portageGetJobCount(FmConst.portageCfgMakeConf)
            FmUtil.portagePatchRepository(repoName2, self.getRepoDir(self._repoName), "S-patch", modDir, jobCount)


class RepositoryCheckError(Exception):

    def __init__(self, message):
        self.message = message
