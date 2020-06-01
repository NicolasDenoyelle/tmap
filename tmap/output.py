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
from socket import gethostname
from random import shuffle
from application import Application, args_str, hostname_regex
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
        
    def gen_permutations(self,
                         num_canonical = 100,
                         num_symmetrics = 100,
                         num_threads = topology.get_nbobjs_by_type('Core')):
        ret = {}    
        # Class for computing canonical permutations
        permutation = TreePermutation(self.topology.dup())
        
        canonicals = set()
        for i in range(num_canonical):
            y = tuple(permutation.shuffled().canonical()[0:num_threads])
            while y in canonicals:
                y = tuple(permutation.shuffled().canonical()[0:num_threads])
            canonicals.add(y)
            ret[y] = (y, num_symmetrics)
            symetrics = set()
            for i in range(num_symmetrics):
                permutation.shuffled_equivalent()
                z = [ x.logical_index for x in permutation.tree if x.is_leaf() ]
                z = tuple([ z[i] for i in y ])
                while z in symetrics or z == y:
                    permutation.shuffled_equivalent()
                z = [ x.logical_index for x in permutation.tree if x.is_leaf() ]
                z = tuple([ z[i] for i in y ])
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
        PUs = [ n for n in self.host.topology \
                if n.type == 'PU' and n.logical_index in symmetric ]
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
