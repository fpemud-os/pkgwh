# testCommandOututSet.py -- Portage Unit Testing Functionality
# Copyright 2007-2020 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

from pkgwh.process import find_binary
from pkgwh.tests import TestCase, test_cps
from pkgwh._sets.shell import CommandOutputSet

class CommandOutputSetTestCase(TestCase):
	"""Simple Test Case for CommandOutputSet"""

	def setUp(self):
		pass

	def tearDown(self):
		pass

	def testCommand(self):

		params = set(test_cps)
		command = find_binary("bash")
		command += " -c '"
		for a in params:
			command += " echo -e \"%s\" ; " % a
		command += "'"
		s = CommandOutputSet(command)
		atoms = s.getAtoms()
		self.assertEqual(atoms, params)
