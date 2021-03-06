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
parser.add_argument('-p', '--permutation', default = "0",
                    help='Input permutation.'\
                    'If it is an integer it is used as the permutation id.'\
                    'If it is a string it is considered to be an index which items '\
                    'are seperated with "seperator".')
parser.add_argument('-if', '--input-file', type=str,
                    help='An input file with one permutation per line in the format'\
                    'allowed by "-p" option.')
parser.add_argument('-sep', '--separator', type=str, default = ' ',
                    help='Separator to use when input permutation is a list of index'\
                    'or when output format is a list.')
parser.add_argument('-r', '--random', default = False, action='store_true',
                    help='Shuffle input permutation.')
parser.add_argument('-t', '--topology', type=str,
                    help='Use a hwloc topology, xml or synthetic string, as'\
                    'a tree to map on permutation.')
parser.add_argument('--topology-leaf', type=str, default='Core',
                    help='Prune topology below object type.')
parser.add_argument('-c', '--canonical', action='store_true', default=False,
                    help='Input permutation is turned into its canonical representation.'\
                    'This option is processed after "random" option.')
parser.add_argument('-s', '--symmetry', action='store_true', default=False,
                    help='Input permutation is shuffled by shuffling tree nodes.'\
                    'This option is processed after "canonical" option.')
parser.add_argument('-of', '--output-format', type=str, choices = ['id', 'list', 'topology'], default = 'id',
                    help='Output format')
args = parser.parse_args()

# Check args
if args.canonical and args.topology is None:
    raise ValueError('Canonical permutations require a tree topology.')
if args.symmetry and args.topology is None:
    raise ValueError('Symmetric permutations require a tree topology.')

# Make topology if possible and check input permutation length is valid.
if args.topology is not None:
    if len(args.topology) < 2:
        args.topology = Topology()        
    else:
        args.topology = Topology(input_topology=args.topology)
    args.topology.singlify(args.topology_leaf)
    n = len([ n for n in args.topology if n.is_leaf()])
else:
    if args.output_format == 'topology':
        raise ValueError('Output format can only be a topology if a topology is used as input.')

    if args.n is not None and args.n != n:
        raise ValueError('The number of tree leaves ({}) and '\
                         'input permutation length ({}) do not match'.format(args.n, n))
    else:
        args.n = n

def do_permutation(permutation):
    # Parse input permutation. If list, check its length is valid()
    try:
        pid = int(permutation)
    except ValueError:
        permutation = Permutation([ int(i) for i in permutation.split(args.separator)])
        if args.n is not None and len(permutation) != args.n:
            raise ValueError('Expected input permutation length ({})'\
                             'do not match permutation length({}).'.format(args.n,
                                                                           len(permutation)))
        pid = Permutation(permutation).id()
    if args.topology is not None:
        permutation = TreePermutation(args.topology, pid)
    elif args.n is not None:
        permutation = Permutation(args.n, pid)
    else:
        permutation = Permutation(permutation)

    if args.random:
        permutation.shuffle()
    if args.symmetry:
        permutation.shuffle_nodes()
    if args.canonical:
        permutation.canonical()

    # Output permutation
    if args.output_format == 'id':
        print(str(permutation.id()))
    if args.output_format == 'list':
        print(args.separator.join([ str(i) for i in permutation.elements ]))
    if args.output_format == 'topology':
        print(str(permutation.tree))
        print(args.separator.join([ str(i) for i in permutation.elements ]))

if args.input_file is None:
    do_permutation(args.permutation)
else:
    with open(args.input_file) as f:
        for l in f.readlines():
            do_permutation(l)
