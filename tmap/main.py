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
from copy import deepcopy
from random import randrange
from socket import gethostname
from application import Application, applications
from topology import Topology, topology
from permutation import Permutation, TreePermutation
from tree import TreeIterator

def args_str(*args, **kwargs):
    fmt = re.compile('\w+')

    args_list=[]
    for arg in args:
        if fmt.match(str(arg)) is None:
            raise ValueError('arg: "{!s}" error. Expected arg format: [0-9a-zA-Z_]'.format(str(arg)))
        args_list.append('{!s}'.format(arg))
        
    for k,v in kwargs.items():
        k = str(k)

        if v is not None:
            v = str(v)
            if fmt.match(v) is None:
                raise ValueError('kwarg: {} error. Expected arg format: [0-9a-zA-Z_]'.format(v))
            if len(k) == 1:
                args_list.append('-{!s}={!s}'.format(k,v))
            else:
                args_list.append('--{!s}={!s}'.format(k,v))
        else:
            if len(k) == 1:
                args_list.append('-{}'.format(k))
            else:
                args_list.append('--{}'.format(k))
    return ':'.join(args_list)
    
def run(app: Application, symmetric, canonical, *args, **kwargs):
    PUs = [ n for n in topology if n.type == 'PU' and n.logical_index in symmetric ]
    app.bind(PUs)
    seconds = app.run(*args, **kwargs)
    sargs = args_str(*args, **kwargs)
    sy = ':'.join([str(i) for i in symmetric])
    sz = ':'.join([str(i) for i in canonical])
    output = '"{}" "{}" {} "{}" {}'.format(sy, sz, app.name(), sargs, seconds)
    print(output)
    return output

def gen_permutations(num_canonical = 100, num_symmetrics = 100, output_file=None):
    ret = {}
    
    num_cores = topology.get_nbobjs_by_type('Core')
    
    # Class for computing canonical permutations
    permutation = TreePermutation(Topology())

    canonicals = set()
    for i in range(num_canonical):
        y = tuple(permutation.shuffled().canonical()[0:num_cores])
        while y in canonicals:
            y = tuple(permutation.shuffled().canonical()[0:num_cores])
        canonicals.add(y)
        ret[y] = (y, num_symmetrics)
        local = set()
        for i in range(num_symmetrics):
            permutation.shuffled_equivalent()
            z = [ x.logical_index for x in permutation.tree if x.is_leaf() ]
            z = tuple([ z[i] for i in y ])
            while z in local or z == y:
                permutation.shuffled_equivalent()
                z = [ x.logical_index for x in permutation.tree if x.is_leaf() ]
                z = tuple([ z[i] for i in y ])
            ret[z] = (y, 1)

    if output_file is not None:
        out = open(output_file, 'w')
        for z, (y, n) in ret.items():
            sy = ':'.join([str(i) for i in y])
            sz = ':'.join([str(i) for i in z])
            out.write('{} {} {}\n'.format(sz, sy, n))
        
    return ret

def read_permutations(file):
    perms = {}
    if not os.path.isfile(file):
        raise FileNotFoundError()
    with open(file, 'r') as f:
        for l in f.readlines():
            symmetric, canonical, n = l.split()
            canonical = tuple([ int(i) for i in canonical.split(':') ])
            symmetric = tuple([ int(i) for i in symmetric.split(':') ])
            n = int(n)
            perms[symmetric] = (canonical, n)
    return perms

class Case:
    def __init__(self, app: Application, *args, hostname=gethostname(), **kwargs):
        hostname = re.match('[a-zA-Z_\-]+', hostname).group()
        basename = os.path.basename(app.dir())
        args_id = args_str(*args, **kwargs)
        self.application = app
        self.app_args = args
        self.app_kwargs = kwargs
        self.permutation_file = hostname + '-permutations.txt'        
        self.output_file = '{}{}{}-{}{}{}-results.txt'.format(os.getcwd(),
                                                              os.path.sep,
                                                              basename,
                                                              hostname,
                                                              os.path.sep,
                                                              args_id)

        if not os.path.isfile(self.permutation_file):
            gen_permutations(100, 100, self.permutation_file)
    
    def remaining_permutations(self):
        permutations = read_permutations(self.permutation_file)
        try:
            f = open(self.output_file, 'r')
            for l in f.readlines():
                symmetric, _, _, _, _ = l.split()
                symmetric = tuple([ str(i) for i in symmetric.strip('"').split(':') ])
                try:
                    permutations[symmetric] -= 1
                    if permutations[p] <= 0:
                        del(permutations[symmetric])
                except KeyError:
                    pass
        except FileNotFoundError:
            pass
        return permutations

    def __iter__(self):
        return self

    def __next__(self):
        permutations = self.remaining_permutations()
        items = list(iter(permutations.items()))
        n = len(items)
        if n == 0:
            raise StopIteration
        k = randrange(n)
        symmetric, (canonical, n) = items[k]
        out = run(self.application, symmetric, canonical,
                  *self.app_args, **self.app_kwargs)

        try:
            f = open(self.output_file, 'a')
        except FileNotFoundError:
            f = open(self.output_file, 'x')
        f.write(out + '\n')
        f.flush()

if __name__ == '__main__':
    bin = sys.argv[0]
    sys.argv = sys.argv[1:]
    apps = applications.keys()
    actions = [ 'rem', 'run' ]
    action = 'run'
    num_canonical = 100
    num_symmetrics = 100
    
    cases = {
        'NAS':  [
            [ 'cg' ], 
            [ 'dc' ],
            [ 'ep' ],
            [ 'ft' ],
            [ 'is' ],
            [ 'lu' ],
            [ 'mg' ],
            [ 'sp' ],
            [ 'ua' ],
        ]
    }

    def remaining(hostname, _cases = cases):
        tot = 0
        for k,v in _cases.items():
            app = applications[k]
            for args in v:
                case = Case(app, *args, hostname=hostname)
                permutations = case.remaining_permutations()
                tot += sum([ n for _, (_, n) in permutations.items() ])
        return tot

    def parse_cases(args):
        if len(args) == 0:
            return cases
        app = args[0]
        if len(args) == 1:
            return cases[app]
        tot = [ i for i in range(len(cases[app])) if all([a in cases[app][i] for a in args[1:]]) ]
        return { app: [ cases[app][i] for i in tot ] }
    
    def usage():
        print('{} <action> (action_args ...)\n'.format(bin))
        print('ACTIONS:\n')
        print("""\t rem (hostname) (): print the number of remaining cases.""")
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

    if action == 'rem':
        hostname = sys.argv[1] if len(sys.argv) > 1 else gethostname()
        _cases = parse_cases(sys.argv[2:])
        print(remaining(hostname, _cases))
        sys.exit(0)
    
    if action == 'run':
        _cases = parse_cases(sys.argv[1:])
        for k,v in _cases.items():
            app = applications[k]
            for args in v:
                case = Case(app, *args)
                for i in iter(case):
                    pass
        sys.exit(0)
