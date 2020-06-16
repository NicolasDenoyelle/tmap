###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import subprocess

from tmap.tree import Tree, Trandom, Tleaf, TreeIterator, ScatterTreeIterator
from tmap.permutation import Permutation, TreePermutation, PermutationIterator, CanonicalPermutationIterator
from tmap.topology import hwloc_version

__all__ = [
    'Tree', 'Trandom', 'Tleaf', 'TreeIterator', 'ScatterTreeIterator',
    'Permutation', 'TreePermutation',
    'PermutationIterator', 'CanonicalPermutationIterator'
]

if hwloc_version is not None:
    from tmap.topology import Topology, topology
    __all__.append('Topology')
    __all__.append('topology')
