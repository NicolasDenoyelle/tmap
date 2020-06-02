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

cases = [
    Case(applications['NAS'], 'cg'),
    Case(applications['NAS'], 'ep'),
    Case(applications['NAS'], 'ft'),
    Case(applications['NAS'], 'is'),
    Case(applications['NAS'], 'lu'),
    Case(applications['NAS'], 'mg'),
    Case(applications['NAS'], 'sp'),
    Case(applications['lulesh']),
    Case(applications['lulesh'], b=4),
    Case(applications['lulesh'], r=3),
    Case(applications['lulesh'], b=4, r=32),
]

actions = [ 'rem', 'run' ]

def usage():
    print('{} <action> <action_args> ...\n'.format(bin))
    print('ACTIONS:\n')
    print("""\t rem (hostname) (): print the number of remaining cases.""")
    print("""\t run (<app>) (<args> ...): run all applications. If a specific 
    permutation file with num_canonical permutations and num_symmetrics 
    permutations per canonical permutation""")

def parse_cases(args, hostname):
    if len(args) == 0:
        return cases
    if len(args) == 1:
        return [ c for c in cases if c.application.name() == args[0] ]
    return [ Case.from_string(args[0], ' '.join(args[1:]), hostname) ]

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
    hostname = gethostname()

    if action == 'rem':
        if sys.argv[1] in applications.keys():
            todo =  parse_cases(sys.argv[1:], hostname)
        else:
            todo =  parse_cases(sys.argv[2:], sys.argv[1])            
        print(sum([ c.count_remainings() for c in todo if c in cases ]))
        sys.exit(0)
    
    if action == 'run':
        for case in parse_cases(sys.argv[1:], hostname):
            if case not in cases:
                continue
            for i in iter(case):
                pass
        sys.exit(0)
