###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

from tree import Tree, TreeIterator
from permutation import TreePermutation
import subprocess
import re

"""
Use hwloc-info and hwloc-calc command line utilities to
create a Tree based on a machine topology.
"""
class Topology(Tree):
    """
    Invoke hwloc-info and parse output to collect some attributes 
    of a topology object.
    @return dict
    """
    @staticmethod
    def attributes(type: str, logical_index: int, input_topology=None):
        cmd = 'hwloc-info'
        if input_topology is not None:
            cmd += ' --input {}'.format(input_topology)
        cmd += ' {}:{}'.format(type, logical_index)
        out = subprocess.getstatusoutput(cmd)
        if out[0] != 0:
            raise ValueError('Invalid topology file')
        
        lines = out[1].split('\n')
        ret = {
            'logical_index': logical_index,
            'memory_children': 0,
            'os_index': None,
            'type': type,
            'cpuset': None,
            'nodeset': None
        }

        type_re = re.compile('^\stype\s=\s(?P<i>\w+)$')
        lindex_re = re.compile('^\slogical\sindex\s=\s(?P<i>\d+)$')
        osindex_re = re.compile('^\sos\sindex\s=\s(?P<i>\d+)$')
        memchild_re = re.compile('^\smemory\schildren\s=\s(?P<i>\d+)$')
        cpuset_re = re.compile('^\scpuset\s=\s(?P<i>\w+)$')
        nodeset_re = re.compile('^\snodeset\s=\s(?P<i>\w+)$')
        
        for line in lines:
            match = type_re.match(line)
            if match is not None:
                ret['type'] = match.group(1)                
            match = cpuset_re.match(line)
            if match is not None:
                ret['cpuset'] = match.group(1)
            match = type_re.match(line)
            if match is not None:
                ret['nodeset'] = match.group(1)
            match = lindex_re.match(line)
            if match is not None:
                ret['logical_index'] = int(match.group(1))
            match = osindex_re.match(line)
            if match is not None:
                ret['os_index'] = int(match.group(1))
            match = memchild_re.match(line)
            if match is not None:
                ret['memory_children'] = int(match.group(1))

        return ret

    """
    Invoke hwloc-calc to get the number of children of @child_type of a topology
    object of a certain @type and @logical_index.
    @return int
    """
    @staticmethod
    def n_children(type: str, logical_index: int, child_type: str, input_topology=None):
        cmd = 'hwloc-calc'
        if input_topology is not None:
            cmd += ' --input {}'.format(input_topology)
        cmd += ' {}:{} -N {}'.format(type, logical_index, child_type)
        out = subprocess.getstatusoutput(cmd)
        if out[0] != 0:
            raise ValueError('Invalid types ot topology file')
        return int(out[1])

    """
    Invoke 'hwloc-info' to retrieve a list of objects in the topology with 
    their type, count and depth.
    If structure is True, topology is filtered to keep objects important for 
    the structure.
    If no_smt is True, PU objects are filtered.
    If no_io is True, io objects are filtered.
    @return [ dict ] sorted by 'depth' key.
    """
    @staticmethod
    def objects(structure=True, no_smt=True, no_io=True, input_topology=None):
        regex = re.compile('(Special\s)?depth\s(?P<depth>\-?\d+):' +
                           '[\s]+(?P<count>[-]?\d+)[\s]+(?P<type>\w+)')
        cmd = "hwloc-info"
        if input_topology is not None:
            cmd += ' --input {}'.format(input_topology)
        if structure:
            cmd += ' --filter all:structure'
        if no_io:
            cmd += ' --no-io'
            
        output = subprocess.getstatusoutput(cmd)
        if output[0] != 0:
            raise ValueError('Invalid topology file')
        output = output[1].split('\n')
            
        objects = [ regex.match(i.strip()) for i in output ]
        objects = [ i.groupdict() for i in objects if i is not None ]
        objects = [ o for o in objects if not no_smt or o['type'] != 'PU' ]
        for o in objects:
            o['depth'] = int(o['depth'])
            o['count'] = int(o['count'])
        objects.sort(key=lambda i: i['depth'])
        return objects

    """
    Topology Tree constructor.
    If structure is True, topology is filtered to keep objects important for 
    the structure.
    If no_smt is True, PU objects are filtered.
    If no_io is True, io objects are filtered.
    """
    def __init__(self, structure=True, no_smt=True, no_io=True, input_topology=None):
        objects = Topology.objects(structure, no_smt, no_io, input_topology)
        
        super().__init__(annotation = Topology.attributes('Machine', 0, input_topology))
        self.annotation['special_objs'] = [ { 'depth': o['depth'],
                                              'type': o['type'],
                                              'count': o['count'], }\
                                            for o in objects if o['depth'] < 0 ]

        for o in [ o for o in objects[:len(objects)] if o['depth'] > 0 ]:
            logical_index = 0
            for leaf in TreeIterator(self, lambda n: n.is_leaf()):
                n = Topology.n_children(leaf.annotation['type'],
                                        leaf.annotation['logical_index'],
                                        o['type'], input_topology)
                leaf.connect_children([
                    Tree(annotation = Topology.attributes(o['type'],
                                                          logical_index+i,
                                                          input_topology))
                    for i in range(n) ])
                logical_index += n

"Pre initialized current machine topology."
topology = Topology()

__all__ = [ 'Topology', 'topology' ]

if __name__ == '__main__':
    for i in TreeIterator(topology):
        print(i.annotation)
