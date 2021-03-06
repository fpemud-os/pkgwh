#!/usr/bin/env python3

import sys
import distutils.util
from setuptools import setup
from setuptools.command.build_py import build_py

# check Python's version
if sys.version_info < (3, 8):
    sys.stderr.write('This module requires at least Python 3.8\n')
    sys.exit(1)

# check linux platform
platform = distutils.util.get_platform()
if not platform.startswith('linux'):
    sys.stderr.write("This module is not available on %s\n" % platform)
    sys.exit(1)

classif = [
    'Development Status :: 5 - Production/Stable',
    'Environment :: Console',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GPLv3 License',
    'Natural Language :: English',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Topic :: Software Development :: Libraries :: Python Modules',
]

# Do setup
setup(
    name='bbki',
    version='0.0.1',
    description='Manage BIOS, Bootloader, Kernel and Initramfs',
    author='Fpemud',
    author_email='fpemud@sina.com',
    license='GPLv3 License',
    platforms='Linux',
    classifiers=classif,
    url='http://github.com/fpemud/bbki',
    download_url='',
    packages=['bbki'],
    package_dir={
        'bbki': 'python3/bbki',
    },
    package_data={
        'bbki': ['kernel-config-rules/*', 'script-helpers/*', 'script-helpers/*/*'],
    },
)
