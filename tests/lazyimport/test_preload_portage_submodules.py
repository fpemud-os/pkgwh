# Copyright 2010 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import pkgwh
from pkgwh.tests import TestCase

class PreloadPortageSubmodulesTestCase(TestCase):

	def testPreloadPortageSubmodules(self):
		"""
		Verify that _preload_portage_submodules() doesn't leave any
		remaining proxies that refer to the pkgwh.* namespace.
		"""
		pkgwh.proxy.lazyimport._preload_portage_submodules()
		for name in pkgwh.proxy.lazyimport._module_proxies:
			self.assertEqual(name.startswith('pkgwh.'), False)
