#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import glob

for fn in glob.glob("*.ebuild"):
    with open(fn, "a") as f:
        f.write("""
pkg_extra_files() {
        # the following file is generated by "/usr/bin/update-desktop-database"
        echo "/usr/share/applications/mimeinfo.cache"
}
""")
