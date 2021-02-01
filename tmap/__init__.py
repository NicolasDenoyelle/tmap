###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import subprocess

from tmap import tree
from tmap import permutation

__all__ = [ 'tree', 'permutation' ]

try:
    from tmap import hwloc_version
    if hwloc_version is not None:
        from tmap.topology import Topology, topology
        __all__.append('Topology')
        __all__.append('topology')
except Exception:
    pass
