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
from tmap import topology

__all__ = [ 'tree', 'permutation' ]

if topology.hwloc_version is not None:
    from tmap.topology import Topology, topology
    __all__.append('Topology')
    __all__.append('topology')
