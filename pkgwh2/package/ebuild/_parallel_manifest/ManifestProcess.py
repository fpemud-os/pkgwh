# Copyright 2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import pkgwh
from pkgwh import os
from pkgwh.exception import (FileNotFound,
	PermissionDenied, PortagePackageException)
from pkgwh.localization import _
from pkgwh.util._async.ForkProcess import ForkProcess

class ManifestProcess(ForkProcess):

	__slots__ = ("cp", "distdir", "fetchlist_dict", "repo_config")

	MODIFIED = 16

	def _run(self):
		mf = self.repo_config.load_manifest(
			os.path.join(self.repo_config.location, self.cp),
			self.distdir, fetchlist_dict=self.fetchlist_dict)

		try:
			mf.create(assumeDistHashesAlways=True)
		except FileNotFound as e:
			pkgwh.writemsg(_("!!! File %s doesn't exist, can't update "
				"Manifest\n") % e, noiselevel=-1)
			return 1

		except PortagePackageException as e:
			pkgwh.writemsg(("!!! %s\n") % (e,), noiselevel=-1)
			return 1

		try:
			modified = mf.write(sign=False)
		except PermissionDenied as e:
			pkgwh.writemsg("!!! %s: %s\n" % (_("Permission Denied"), e,),
				noiselevel=-1)
			return 1
		else:
			if modified:
				return self.MODIFIED
			return os.EX_OK
