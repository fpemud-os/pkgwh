# Copyright 2010 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import pkgwh
from pkgwh import os
from pkgwh.const import CACHE_PATH, PROFILE_PATH

def _get_legacy_global(name):
	constructed = pkgwh._legacy_globals_constructed
	if name in constructed:
		return getattr(portage, name)

	if name == 'portdb':
		pkgwh.portdb = pkgwh.db[pkgwh.root]["porttree"].dbapi
		constructed.add(name)
		return getattr(portage, name)

	if name in ('mtimedb', 'mtimedbfile'):
		pkgwh.mtimedbfile = os.path.join(pkgwh.settings['EROOT'],
			CACHE_PATH, "mtimedb")
		constructed.add('mtimedbfile')
		pkgwh.mtimedb = pkgwh.MtimeDB(pkgwh.mtimedbfile)
		constructed.add('mtimedb')
		return getattr(portage, name)

	# Portage needs to ensure a sane umask for the files it creates.
	os.umask(0o22)

	kwargs = {}
	for k, envvar in (("config_root", "PORTAGE_CONFIGROOT"),
			("target_root", "ROOT"), ("sysroot", "SYSROOT"),
			("eprefix", "EPREFIX")):
		kwargs[k] = os.environ.get(envvar)

	pkgwh._initializing_globals = True
	pkgwh.db = pkgwh.create_trees(**kwargs)
	constructed.add('db')
	del pkgwh._initializing_globals

	settings = pkgwh.db[pkgwh.db._target_eroot]["vartree"].settings

	pkgwh.settings = settings
	constructed.add('settings')

	# Since pkgwh.db now uses EROOT for keys instead of ROOT, we make
	# pkgwh.root refer to EROOT such that it continues to work as a key.
	pkgwh.root = pkgwh.db._target_eroot
	constructed.add('root')

	# COMPATIBILITY
	# These attributes should not be used within
	# Portage under any circumstances.

	pkgwh.archlist = settings.archlist()
	constructed.add('archlist')

	pkgwh.features = settings.features
	constructed.add('features')

	pkgwh.groups = settings.get("ACCEPT_KEYWORDS", "").split()
	constructed.add('groups')

	pkgwh.pkglines = settings.packages
	constructed.add('pkglines')

	pkgwh.selinux_enabled = settings.selinux_enabled()
	constructed.add('selinux_enabled')

	pkgwh.thirdpartymirrors = settings.thirdpartymirrors()
	constructed.add('thirdpartymirrors')

	profiledir = os.path.join(settings["PORTAGE_CONFIGROOT"], PROFILE_PATH)
	if not os.path.isdir(profiledir):
		profiledir = None
	pkgwh.profiledir = profiledir
	constructed.add('profiledir')

	return getattr(portage, name)
