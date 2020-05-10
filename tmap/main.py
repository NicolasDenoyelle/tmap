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
                                               app.name(), sargs,
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
            for line in f.readlines():
                p = Permutation(line.split()[0].strip('"'))
                try:
                    permutations[p] -= 1
                    if permutations[p] <= 0:
                        del(permutations[p])
                except KeyError:
                    pass
        except FileNotFoundError:
            pass
        return permutations

    def __iter__(self):
        return self

    def __next__(self):
        permutations = self.remaining_permutations()
        keys = list(iter(permutations.keys()))
        n = len(keys)
        if n == 0:
            raise StopIteration
        k = randrange(n)
        out = run(self.application, keys[k], *self.app_args, **self.app_kwargs)

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
                tot += sum(permutations.values())
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
                                               app.name(), sargs,
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
            for line in f.readlines():
                p = Permutation(line.split()[0].strip('"'))
                try:
                    permutations[p] -= 1
                    if permutations[p] <= 0:
                        del(permutations[p])
                except KeyError:
                    pass
        except FileNotFoundError:
            pass
        return permutations

    def __iter__(self):
        return self

    def __next__(self):
        permutations = self.remaining_permutations()
        keys = permutations.keys()
        n = len(keys)
        if n == 0:
            raise StopIteration
        keys = iter(keys)
        for i in range(randrange(n)):
            k = next(keys)
        out = run(self.application, k, *self.app_args, **self.app_kwargs)
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
            ([ 'cg' ], {}), 
            ([ 'dc' ], {}),
            ([ 'cg' ], {}),
            ([ 'ep' ], {}),
            ([ 'ft' ], {}),
            ([ 'is' ], {}),
            ([ 'lu' ], {}),
            ([ 'mg' ], {}),
            ([ 'sp' ], {}),
            ([ 'ua' ], {})
        ]
    }

    def remaining(hostname, _cases = cases):
        tot = 0
        for k,v in _cases.items():
            app = applications[k]
            for args, kwargs in v:
                kwargs['hostname'] = hostname
                case = Case(app, *args, **kwargs)
                permutations = case.remaining_permutations()
                tot += sum(permutations.values())
        return tot
    
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
        print(remaining(hostname))
        sys.exit(0)
    
    if action == 'run':
        if len(sys.argv) <= 1:
            for k,v in cases.items():
                app = applications[k]
                for args, kwargs in v:
                    case = Case(app, *args, **kwargs)
                    for i in iter(case):
                        pass
            sys.exit(0)
        if len(sys.argv) > 1:
            app = applications[sys.argv[1]]
            _cases = cases[sys.argv[1]]
            if len(sys.argv) > 2:
                _cases = [ (sys.argv[2:], {}) ]
            for args, kwargs in _cases:
                case = Case(app, *args, **kwargs)
                for i in iter(case):
                    pass
