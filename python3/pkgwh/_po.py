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
import anytree
from ._util import Util
from ._exception import RunningEnvironmentError


class KernelType:

    LINUX = "linux"


class BootMode:

    EFI = "efi"
    BIOS = "bios"


class FsLayout:

    def __init__(self, bbki):
        self._bbki = bbki

    def get_boot_dir(self):
        return "/boot"

    def get_lib_dir(self):
        return "/boot"

    def get_boot_history_dir(self):
        return "/boot/history"

    def get_boot_grub_dir(self):
        return "/boot/grub"

    def get_boot_grub_efi_dir(self):
        return "/boot/EFI"

    def get_boot_rescue_os_dir(self):
        return "/boot/rescue"

    def get_boot_rescue_os_kernel_filepath(self):
        return "/boot/rescue/vmlinuz"

    def get_boot_rescue_os_initrd_filepath(self):
        return "/boot/rescue/initrd.img"

    def get_firmware_dir(self):
        return "/lib/firmware"


def _getUnderlayDisk(devPath, parent=None):
    # HostDiskLvmLv
    lvmInfo = Util.getBlkDevLvmInfo(devPath)
    if lvmInfo is not None:
        bdi = HostDiskLvmLv(Util.getBlkDevUuid(devPath), lvmInfo[0], lvmInfo[1], parent=parent)
        for slaveDevPath in Util.lvmGetSlaveDevPathList(lvmInfo[0]):
            _getUnderlayDisk(slaveDevPath, parent=bdi)
        return bdi

    # HostDiskPartition
    m = re.fullmatch("(/dev/sd[a-z])[0-9]+", devPath)
    if m is None:
        m = re.fullmatch("(/dev/xvd[a-z])[0-9]+", devPath)
        if m is None:
            m = re.fullmatch("(/dev/vd[a-z])[0-9]+", devPath)
            if m is None:
                m = re.fullmatch("(/dev/nvme[0-9]+n[0-9]+)p[0-9]+", devPath)
    if m is not None:
        bdi = HostDiskPartition(Util.getBlkDevUuid(devPath), HostDiskPartition.PART_TYPE_MBR, parent=parent)        # FIXME: currently there's no difference when processing mbr and gpt partition
        _getUnderlayDisk(m.group(1), parent=bdi)
        return bdi

    # HostDiskScsiDisk
    m = re.fullmatch("/dev/sd[a-z]", devPath)
    if m is not None:
        return HostDiskScsiDisk(Util.getBlkDevUuid(devPath), Util.scsiGetHostControllerName(devPath), parent=parent)

    # HostDiskXenDisk
    m = re.fullmatch("/dev/xvd[a-z]", devPath)
    if m is not None:
        return HostDiskXenDisk(Util.getBlkDevUuid(devPath), parent=parent)

    # HostDiskVirtioDisk
    m = re.fullmatch("/dev/vd[a-z]", devPath)
    if m is not None:
        return HostDiskVirtioDisk(Util.getBlkDevUuid(devPath), parent=parent)

    # HostDiskNvmeDisk
    m = re.fullmatch("/dev/nvme[0-9]+n[0-9]+", devPath)
    if m is not None:
        return HostDiskNvmeDisk(Util.getBlkDevUuid(devPath), parent=parent)

    # HostDiskBcache
    m = re.fullmatch("/dev/bcache[0-9]+", devPath)
    if m is not None:
        bdi = HostDiskBcache(Util.getBlkDevUuid(devPath), parent=parent)
        slist = Util.bcacheGetSlaveDevPathList(devPath)
        for i in range(0, len(slist)):
            if i < len(slist) - 1:
                bdi.add_cache_dev(_getUnderlayDisk(slist[i], parent=bdi))
            else:
                bdi.add_backing_dev(_getUnderlayDisk(slist[i], parent=bdi))
        return bdi

    # unknown
    raise RunningEnvironmentError("unknown device \"%s\"" % (devPath))
