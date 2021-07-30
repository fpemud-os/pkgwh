# Copyright 1999-2014 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

import pkgwh
from pkgwh import os
from pkgwh.util import writemsg_level
from pkgwh.sync.syncbase import NewBase


class CVSSync(NewBase):
	'''CVS sync module'''

	short_desc = "Perform sync operations on CVS repositories"

	@staticmethod
	def name():
		return "CVSSync"


	def __init__(self):
		NewBase.__init__(self, "cvs", pkgwh.const.CVS_PACKAGE_ATOM)


	def exists(self, **kwargs):
		'''Tests whether the repo is checked out'''
		return os.path.exists(os.path.join(self.repo.location, 'CVS'))


	def new(self, **kwargs):
		if kwargs:
			self._kwargs(kwargs)
		#initial checkout
		cvs_root = self.repo.sync_uri
		if pkgwh.process.spawn_bash(
			"cd %s; exec cvs -z0 -d %s co -P -d %s %s" %
			(pkgwh._shell_quote(os.path.dirname(self.repo.location)), pkgwh._shell_quote(cvs_root),
				pkgwh._shell_quote(os.path.basename(self.repo.location)),
				pkgwh._shell_quote(self.repo.module_specific_options["sync-cvs-repo"])),
				**self.spawn_kwargs) != os.EX_OK:
			msg = "!!! cvs checkout error; exiting."
			self.logger(self.xterm_titles, msg)
			writemsg_level(msg + "\n", noiselevel=-1, level=logging.ERROR)
			return (1, False)
		return (0, False)


	def update(self):
		"""
		Internal function to update an existing CVS repository

		@return: tuple of return code (0=success), whether the cache
			needs to be updated
		@rtype: (int, bool)
		"""

		#cvs update
		exitcode = pkgwh.process.spawn_bash(
			"cd %s; exec cvs -z0 -q update -dP" % \
			(pkgwh._shell_quote(self.repo.location),),
			**self.spawn_kwargs)
		if exitcode != os.EX_OK:
			msg = "!!! cvs update error; exiting."
			self.logger(self.xterm_titles, msg)
			writemsg_level(msg + "\n", noiselevel=-1, level=logging.ERROR)
		return (exitcode, False)
