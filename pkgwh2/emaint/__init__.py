# Copyright 2005-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

"""System health checks and maintenance utilities.
"""

import os
from pkgwh.module import Modules


def get_action_runners(module_name, action):
    # Similar to emerge, emaint needs a default umask so that created
    # files (such as the world file) have sane permissions.
    os.umask(0o22)

    self_dir = os.path.dirname(os.path.realpath(__file__))
    module_path = os.path.join(self_dir, "modules")
    module_controller = Modules(path=module_path, namepath="pkgwh.emaint.modules")
    assert "all" not in module_controller.module_names

    tasks = []
    for m in module_controller.module_names:
        if module_name == "all" or module_name == m.name:
            if action in module_controller.get_functions(m):
                tasks.append(module_controller.get_class(m))
            else:
                raise Exception("module '%s' does not have option '%s'\n\n" % (m.name, action))        # FIXME: change Exception to more specific type
            continue

    return tasks    # FIXME: how to run them?
