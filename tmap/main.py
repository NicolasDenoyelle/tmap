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
from output import Case
from application import applications

cases = {
    'NAS':  [
        [ 'cg' ], 
        [ 'ep' ],
        [ 'ft' ],
        [ 'is' ],
        [ 'lu' ],
        [ 'mg' ],
        [ 'sp' ],
    ],
    'lulesh': [
        {},
        { 'b': None },
        { 'r': '3' },
        { 'r': '32', 'b': None },
    ]
}

actions = [ 'rem', 'run' ]

def usage():
    print('{} <action> <action_args> ...\n'.format(bin))
    print('ACTIONS:\n')
    print("""\t rem (hostname) (): print the number of remaining cases.""")
    print("""\t run (<app>) (<args> ...): run all applications. If a specific 
    permutation file with num_canonical permutations and num_symmetrics 
    permutations per canonical permutation""")

def parse_cases(args):
    if len(args) == 0:
        return cases
    app = args[0]
    
    if len(args) == 1:
        return { app: cases[app] }

    subcases = []
    for case in cases[app]:
        if isinstance(case, list) and next((arg in case for arg in args), False):
            subcases.append(case)
            continue
        if isinstance(case, dict):
            flags = [ i in list(zip([ i.strip('-') for i in args ], args[1:]+[ None ])) for i in case.items() ]
            opts = [ i in list(zip([ i.strip('-') for i in args ], [ None for a in args ])) for i in case.items() ]
            if all([ f or o for f,o in zip(flags, opts)]) and (len(flags) > 0 or len(args) == 0):
                subcases.append(case)
                continue
    return { app: subcases }

def remaining(hostname = gethostname(), _cases = cases):
    tot = 0
    for k,v in _cases.items():
        for args in v:
            if isinstance(args, list):
                tot += Case(applications[k], *args, hostname=hostname).count_remainings()
            if isinstance(args, dict):
                tot += Case(applications[k], hostname=hostname, **args).count_remainings()
    return tot

if __name__ == '__main__':
    bin = sys.argv[0]
    sys.argv = sys.argv[1:]

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
        hostname = gethostname()
        if len(sys.argv) > 1 and sys.argv[1] not in cases.keys():
            hostname = sys.argv[1]
            _cases = parse_cases(sys.argv[2:])
        else:
            _cases = parse_cases(sys.argv[1:])
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
