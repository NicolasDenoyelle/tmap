###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import subprocess

from tree import Tree, Tleaf, TreeIterator, ScatterTreeIterator
from permutation import Permutation, TreePermutation
from topology import Topology

all = [
    'Tree',
    'Tleaf',
    'TreeIterator',
    'ScatterTreeIterator',
    'Permutation',
    'TreePermutation'
]

s, _ = subprocess.getstatusoutput('hwloc-info')
if s == 0:
    all.append('Topology')
    
__all__ = all
