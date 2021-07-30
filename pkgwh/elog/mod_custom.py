# elog/mod_custom.py - elog dispatch module
# Copyright 2006-2020 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2

import pkgwh.elog.mod_save
import pkgwh.exception
import pkgwh.process

def process(mysettings, key, logentries, fulltext):
	elogfilename = pkgwh.elog.mod_save.process(mysettings, key, logentries, fulltext)

	if not mysettings.get("PORTAGE_ELOG_COMMAND"):
		raise pkgwh.exception.MissingParameter("!!! Custom logging requested but PORTAGE_ELOG_COMMAND is not defined")
	else:
		mylogcmd = mysettings["PORTAGE_ELOG_COMMAND"]
		mylogcmd = mylogcmd.replace("${LOGFILE}", elogfilename)
		mylogcmd = mylogcmd.replace("${PACKAGE}", key)
		retval = pkgwh.process.spawn_bash(mylogcmd)
		if retval != 0:
			raise pkgwh.exception.PortageException("!!! PORTAGE_ELOG_COMMAND failed with exitcode %d" % retval)
