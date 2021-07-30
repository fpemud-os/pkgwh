# Copyright 2018-2019 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

import os
import subprocess

import pkgwh
from pkgwh.const import pkgwh_PYM_PATH
from pkgwh.tests import TestCase


class WakeupFdSigchldTestCase(TestCase):
	def testWakeupFdSigchld(self):
		"""
		This is expected to trigger a bunch of messages like the following
		unless the fix for bug 655656 works as intended:

		Exception ignored when trying to write to the signal wakeup fd:
		BlockingIOError: [Errno 11] Resource temporarily unavailable
		"""

		script = """
import os
import signal
import sys

import pkgwh

# In order to avoid potential interference with API consumers, wakeup
# fd handling is enabled only when pkgwh._interal_caller is True.
pkgwh._internal_caller = True

from pkgwh.util.futures import asyncio

loop = asyncio._wrap_loop()

# Cause the loop to register a child watcher.
proc = loop.run_until_complete(asyncio.create_subprocess_exec('sleep', '0', loop=loop))
loop.run_until_complete(proc.wait())

for i in range(8192):
	os.kill(pkgwh.getpid(), signal.SIGCHLD)

# Verify that the child watcher still works correctly
# (this will hang if it doesn't).
proc = loop.run_until_complete(asyncio.create_subprocess_exec('sleep', '0', loop=loop))
loop.run_until_complete(proc.wait())
loop.close()
sys.stdout.write('success')
sys.exit(os.EX_OK)
"""

		pythonpath = os.environ.get('PYTHONPATH', '').strip().split(':')
		if not pythonpath or pythonpath[0] != PORTAGE_PYM_PATH:
			pythonpath = [PORTAGE_PYM_PATH] + pythonpath
		pythonpath = ':'.join(filter(None, pythonpath))

		proc = subprocess.Popen(
			[pkgwh._python_interpreter, '-c', script],
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
			env=dict(os.environ, PYTHONPATH=pythonpath))

		out, err = proc.communicate()
		try:
			self.assertEqual(out[:100], b'success')
		except Exception:
			pkgwh.writemsg(''.join('{}\n'.format(line)
				for line in out.decode(errors='replace').splitlines()[:50]),
				noiselevel=-1)
			raise

		self.assertEqual(proc.wait(), os.EX_OK)
