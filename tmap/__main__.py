#!/usr/bin/env python3

###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import argparse
from tmap.permutation import Permutation, TreePermutation
from tmap.topology import Topology

parser = argparse.ArgumentParser()
parser.add_argument('-n', type=int,
                    help='The number of elements in the permutation.')
parser.add_argument('-p', '--permutation', type=int, default = 0,
                    help='Input permutation id')
parser.add_argument('-r', '--random', default = False, action='store_true',
                    help='Shuffle input permutation.')
parser.add_argument('-t', '--topology', type=str,
                    help='Use a hwloc topology, xml or synthetic string, as'\
                    'a tree to map on permutation.')
parser.add_argument('-c', '--canonical', action='store_true', default=False,
                    help='Input permutation is turned into its canonical representation.'\
                    'This option is processed after "random" option.')
parser.add_argument('-s', '--symmetry', action='store_true', default=False,
                    help='Input permutation is shuffled by shuffling tree nodes.'\
                    'This option is processed after "canonical"xs option.')
parser.add_argument('-f', '--format', type=str, choices = ['id', 'list'], default = 'id',
                    help='Output format')
args = parser.parse_args()

# Checking invalid input
if args.n is None and args.topology is None:
    raise ValueError('Either "n" or "topology" option must be set.')
if args.canonical and args.topology is None:
    raise ValueError('Canonical permutations require a tree topology.')
if args.symmetry and args.topology is None:
    raise ValueError('Symmetric permutations require a tree topology.')

# Build permutation
if args.topology:
    permutation = TreePermutation(Topology(args.topology), args.permutation)
else:
    permutation = Permutation(args.n)

# Process input permutation
if args.random:
    permutation = permutation.shuffled()
if args.canonical:
    permutation = permutation.canonical()
if args.symmetry:
    permutation = permutation.shuffled_equivalent()

# Output permutation

if args.format == 'id':
    print(permutation.id())
if args.format == 'list':
    print([ str(i) for i in permutation.elements ].join(' '))
