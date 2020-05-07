###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import os
import re
import sys
from socket import gethostname
from random import randrange
from application import Application, applications
from topology import Topology, topology
from permutation import Permutation, TreePermutation
from tree import TreeIterator

def args_str(*args, **kwargs):
    fmt = re.compile('\w+')
    
    out = ''
    for arg in args:
        if fmt.match(str(arg)) is None:
            raise ValueError('arg: "{!s}" error. Expected arg format: [0-9a-zA-Z_]'.format(str(arg)))
        out += ':{!s}'.format(arg)
        
    for k,v in kwargs.items():
        k = str(k)

        if v is not None:
            v = str(v)
            if fmt.match(v) is None:
                raise ValueError('kwarg: {} error. Expected arg format: [0-9a-zA-Z_]'.format(v))
            if len(k) == 1:
                out.append(':-{!s}={!s}'.format(k,v))
            else:
                out.append(':--{!s}={!s}'.format(k,v))
        else:
            if len(k) == 1:
                out += ':-{}'.format(k)
            else:
                out += ':--{}'.format(k)
    return out
    
def run(app: Application, binding, *args, **kwargs):
    if isinstance(binding, list):
        binding = Permutation(binding)
    if isinstance(binding, Permutation):
        binding = TreePermutation(Topology(), binding.id())
    elif isinstance(binding, int):
        binding = TreePermutation(Topology(), binding)
        
    if not isinstance(binding, TreePermutation):
        raise ValueError('binding must be either: a permutation id, an index, a Permutation or a TreePermutation')
        
    canonical = binding.canonical()
    CUs = [ n for n in TreeIterator(topology, lambda n: n.is_leaf()) ]
    CUs = [ CUs[i] for i in binding ]
    app.bind(CUs)
    seconds = app.run(*args, **kwargs)    
    sargs = args_str(*args, **kwargs)
    output = '"{!s}" "{!s}" {} "{}" {}'.format(binding, canonical,
                                               app.name(), args_str(*args, **kwargs),
                                               seconds)
    print(output)
    return output

def gen_permutations(num_canonical = 100, num_symmetrics = 100, output_file=None):
    if output_file is not None:
        out = open(output_file, 'w')
    permutation = TreePermutation(Topology())
    canonicals = {}
    for i in range(num_canonical):
        y = permutation.shuffled()
        while y in canonicals.keys():
            y = permutation.shuffled()
        canonicals[y] = num_symmetrics
        if output_file is not None:
            out.write(str(y) + ' {}\n'.format(num_symmetrics))
        
    symmetrics = {}
    for y in canonicals.keys():
        local_sym = {}
        for i in range(num_symmetrics):
            z = y.shuffled_equivalent()
            while z in local_sym.keys():
                z = y.shuffled_equivalent()
            local_sym[z] = [ 1, 0 ]
            if output_file is not None:
                out.write(str(z) + ' 1\n')
        for p, n in local_sym.items():
            symmetrics[p] = n
            
    for p, n in canonicals.items():
        symmetrics[p] = n
    return symmetrics

def read_permutations(file):
    perms = {}
    if not os.path.isfile(file):
        raise FileNotFoundError()
    with open(file, 'r') as f:
        for l in f.readlines():
            p, n = l.split()
            p = Permutation([ int(i) for i in p.split(':') ])
            perms[p] = int(n)
    return perms

class Case:
    permutation_file = gethostname() + '-permutations.txt'
    
    def __init__(self, app: Application, *args, **kwargs):
        self.application = app
        self.app_args = args
        self.app_kwargs = kwargs
        self.output_file = app.path + os.path.sep + 'results.txt'
    
    def update_permutations(self):
        if not os.path.isfile(Case.permutation_file):
            raise Exception('Permutation file "{}" has to be generated.'.format(Case.permutation_file))

        self.permutations = read_permutations(Case.permutation_file)
        try:
            f = open(self.output_file, 'r')
            for line in f.readlines():
                p = Permutation(line.split()[0].strip('"'))
                try:
                    self.permutations[p] -= 1
                    if self.permutations[p] <= 0:
                        del(self.permutations[p])
                except KeyError:
                    pass
        except FileNotFoundError:
            pass

    def __iter__(self):
        return self

    def __next__(self):
        self.update_permutations()
        keys = self.permutations.keys()
        n = len(keys)
        if n == 0:
            raise StopIteration
        keys = iter(keys)
        for i in range(randrange(n)):
            k = next(keys)
        out = run(self.application, k, *self.app_args, **self.app_kwargs)
        with open(self.output_file, 'a') as f:
            f.write(out + '\n')

if __name__ == '__main__':
    bin = sys.argv[0]
    sys.argv = sys.argv[1:]
    apps = applications.keys()
    actions = [ 'gen', 'run' ]
    action = 'run'
    num_canonical = 10
    num_symmetrics = 10
    cases = [
        [ 'NAS', [ 'cg' ], {} ],
        [ 'NAS', [ 'dc' ], {} ],
        [ 'NAS', [ 'cg' ], {} ],
        [ 'NAS', [ 'ep' ], {} ],
        [ 'NAS', [ 'ft' ], {} ],
        [ 'NAS', [ 'is' ], {} ],
        [ 'NAS', [ 'lu' ], {} ],
        [ 'NAS', [ 'mg' ], {} ],
        [ 'NAS', [ 'sp' ], {} ],
        [ 'NAS', [ 'ua' ], {} ],
    ]
    
    def usage():
        print('{} <action> (action_args ...)\n'.format(bin))
        print('ACTIONS:\n')
        print("""\t gen (<num_canonical> <num_symmetrics>): generate 
        permutation file with num_canonical permutations and num_symmetrics 
        permutations per canonical permutation""")
        print("""\t run (<app>) (<args> ...): run all applications. If a specific 
        permutation file with num_canonical permutations and num_symmetrics 
        permutations per canonical permutation""")

    if len(sys.argv) == 0 or \
       sys.argv[0] == 'help' or \
       sys.argv[0] == '--help' or \
       sys.argv[0] == '-h':
        usage()
        sys.exit(0)
        
    if len(sys.argv) > 0:
        if sys.argv[0] not in actions:
            usage()
            sys.exit(1)
    action = sys.argv[0]
    
    if action == 'gen':
        if len(sys.argv) >= 3:
            num_canonical = int(sys.argv[1])
            num_symmetrics = int(sys.argv[2])
        gen_permutations(num_canonical, num_symmetrics, Case.permutation_file)
        sys.exit(0)

    if action == 'run':
        if len(sys.argv) <= 1:
            for c in cases:                
                next(iter(Case(applications[c[0]], *list(c[1]), **c[2])))
            sys.exit(0)
        if len(sys.argv) > 1:
            args = []
            app = sys.argv[1]
            if app not in apps:
                raise ValueError('app must be one of {!s}'.format(apps))
        if len(sys.argv) > 2:
            args = sys.argv[2:]
            next(iter(Case(applications[app], *list(args))))
