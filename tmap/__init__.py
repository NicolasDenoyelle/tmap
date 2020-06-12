###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import subprocess

from tmap.tree import Tree, Tleaf, TreeIterator, ScatterTreeIterator
from tmap.permutation import Permutation, TreePermutation
from tmap.topology import Topology

all = [
    'Tree', 'TRandom', 'Tleaf', 'TreeIterator', 'ScatterTreeIterator',
    'Permutation', 'TreePermutation'
    'PermutationIterator', 'CanonicalPermutationIterator'
]

s, _ = subprocess.getstatusoutput('hwloc-info')
if s == 0:
    all.append('Topology')

__all__ = all
