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
from itertools import cycle, islice
from socket import gethostname
from random import shuffle
from application import applications, Application, args_str, hostname_regex, str_args
from tree import TreeIterator
from permutation import TreePermutation
from datetime import datetime
from topology import topology

class Host:
    def __init__(self, hostname = gethostname()):
        self.hostname = hostname
        self.topology = topology.dup()
        self.permutation_file = hostname_regex.match(self.hostname).group() + \
                                '-permutations.txt'
        if not os.path.isfile(self.permutation_file):
            self.gen_permutations()
    
    def __repr__(self):
        hostname_regex.match(self.hostname).group()
    
    def __str__(self):
        return self.hostname

    """
    Compute @num_canonical distinct permutations.
    For each canonical permutation, compute @num_symmetrics distinct 
    permutations.
    Each permutation contains @num_threads index representing a physical PU
    mapped on a @map_by object.
    If @num_threads oversubscribe the number of @map_by in topology, @map_by
    will cycle in a round-robin fashion on the permutation. 
    Resulting permutation are stored in a host local file.
    """
    def gen_permutations(self,
                         num_canonical = 100,
                         num_symmetrics = 100,
                         num_threads = topology.get_nbobjs_by_type('Core'),
                         map_by = 'Core'):
        ret = {}    

        # Make a topology tree with `map_by` leaves.
        topo = self.topology.dup()
        objects = [ n for n in topo if n.type == map_by ]
        for node in objects:
            # Prune children
            for child in node.children:
                child.prune()

        # Class for computing permutations on topology
        permutation = TreePermutation(topo)

        # Set of canonical permutations: PUs os_index
        canonicals = set()
        while len(canonicals) < num_canonical:
            # Compute a random canonical permutation
            canonical = permutation.shuffled().canonical()
            y = tuple([ objects[i].PUs[0].os_index 
                        for i in islice(cycle(canonical.elements), num_threads) ])
            if y in canonicals:
                continue
            canonicals.add(y)            
            ret[y] = (y, num_symmetrics)

        

            # Set of symmetric  permutations: PUs os_index
            symetrics = set()
            while len(symetrics) < num_symmetrics:
                # Compute a random shuffled equivalent permutation
                symmetric = canonical.shuffled_equivalent()
                z = tuple([ objects[i].PUs[0].os_index \
                            for i in islice(cycle(symmetric.elements), num_threads) ])
                symetrics.add(z)
                ret[z] = (y, 1)
                
        with open(self.permutation_file, 'w') as out:
            for z, (y, n) in ret.items():
                out.write('{} {} {}\n'.format(':'.join([str(i) for i in z]),
                                              ':'.join([str(i) for i in y]), n))
        return ret

    def count_permutations(self):
        count = {}
        with open(self.permutation_file, 'r') as f:
            for l in f.readlines():
                symmetric, canonical, n = l.split()
                symmetric = tuple([ int(i) for i in symmetric.split(':') ])
                try:
                    count[symmetric][1] = count[symmetric][1] + int(n)
                except KeyError:
                    canonical = tuple([ int(i) for i in canonical.split(':') ])
                    count[symmetric] = [canonical, int(n)]
        return count
        
class Case:
    def __init__(self, application: Application, *args,
                 hostname=gethostname(), **kwargs):
        self.time = datetime.now()
        self.host = Host(hostname)
        self.application = application
        self.args = args
        self.kwargs = kwargs
        self.str_args = args_str(*args, **kwargs)

    @staticmethod
    def from_string(application: str, args: str, hostname=gethostname()):
        application = applications[application]
        args, kwargs = str_args(args)
        return Case(application, *args, hostname=hostname, **kwargs) 

    def __eq__(self, other):
        if self.application.name() != other.application.name():
            return False
        if self.str_args != other.str_args:
            return False
        return True

    def output_file(self):
        file = self.application.local_dir(str(self.host)) + os.path.sep
        file = file if len(self.str_args) == 0 else file + self.str_args + '_'
        file = '{}{!s}:{!s}:{!s}:{!s}'.format(file,
                                              self.time.date(),
                                              self.time.hour,
                                              self.time.minute,
                                              self.time.second)
        return file
    
    
    def format_result(self, symmetric_permutation: list,
                      canonical_permutation: list, seconds: float):
        z = ':'.join([str(i) for i in symmetric_permutation])
        y = ':'.join([str(i) for i in canonical_permutation])
        return '{} {} {} "{}" {}'.format(z, y, self.application.name(),
                                             self.str_args, seconds)

    def get_filenames(self):
        path = self.application.local_dir(self.host.hostname) + os.path.sep
        files = os.listdir(path)
        datefmt = '\d+-\d+-\d+:\d+:\d+:\d+'
        fmt = datefmt if len(self.str_args) == 0 \
              else '{}_{}'.format(self.str_args, datefmt)
        regex = re.compile(fmt)
        return [ path + f for f in files if regex.match(f) ]

    def count_results(self):
        filenames = self.get_filenames()
        permutations = {}
        
        for filename in filenames:
            with open(filename, 'r') as f:
                for l in f.readlines():
                    symmetric, _, _, _, _ = l.split()
                    symmetric = tuple([ int(i) for i in \
                                        symmetric.split(':') ])
                    try:
                        permutations[symmetric] = permutations[symmetric] + 1
                    except KeyError:
                        permutations[symmetric] = 1
        return permutations

    def remaining_permutations(self):
        done = self.count_results()
        todo = self.host.count_permutations()
        for symmetric, n in done.items():
            try:
                todo[symmetric][1] = todo[symmetric][1] - n
                if todo[symmetric][1] <= 0:
                    del(todo[symmetric])
            except KeyError:
                pass
        return todo

    def count_remainings(self):
        remaining = self.remaining_permutations()
        return sum([n for _, (_, n) in remaining.items()])

    def run(self, symmetric: list, canonical: list):
        PUs = [ self.host.topology.get_obj_by_type('PU', i, True) \
                for i in symmetric ]
        self.application.bind(PUs)
        seconds = self.application.run(*self.args, **self.kwargs)
        output = self.format_result(symmetric, canonical, seconds)
        print(output)
        file = self.output_file()
        try:
            f = open(file, 'a')
        except FileNotFoundError:
            f = open(file, 'x')
        f.write(output + '\n')
        f.flush()
    
    def __iter__(self):
        self.todo = list(self.remaining_permutations().items())
        shuffle(self.todo)
        return self
    
    def __next__(self):
        sym, (can, n) = next(iter(self.todo))
        for i in range(n):
            self.run(sym, can)
        self.todo = self.todo[1:]

if __name__ == '__main__':
    from application import NAS
    c = Case(NAS(), 'cg')
    next(iter(c))
    print(c.count_remainings())
    next(iter(c))
    print(c.count_remainings())
