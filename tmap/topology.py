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
    type_re = re.compile('^\stype\s=\s(?P<i>\w+)$')
    lindex_re = re.compile('^\slogical\sindex\s=\s(?P<i>\d+)$')
    osindex_re = re.compile('^\sos\sindex\s=\s(?P<i>\d+)$')
    memchild_re = re.compile('^\smemory\schildren\s=\s(?P<i>\d+)$')
    cpuset_re = re.compile('^\scpuset\s=\s(?P<i>(\w+,?)+)$')
    nodeset_re = re.compile('^\snodeset\s=\s(?P<i>\w+)$')

    @staticmethod
    def parse_obj_info(info: str):
        logical_index = None
        memory_children = None,
        os_index = None
        type = None
        cpuset = None
        nodeset = None
        for line in info.split('\n'):
            match = Topology.type_re.match(line)
            if match is not None:
                type = match.group(1)                
            match = Topology.cpuset_re.match(line)
            if match is not None:
                cpuset = match.group(1)
            match = Topology.type_re.match(line)
            if match is not None:
                nodeset = match.group(1)
            match = Topology.lindex_re.match(line)
            if match is not None:
                logical_index = int(match.group(1))
            match = Topology.osindex_re.match(line)
            if match is not None:
                os_index = int(match.group(1))
            match = Topology.memchild_re.match(line)
            if match is not None:
                memory_children = int(match.group(1))
                
        node = Tree(logical_index = logical_index,
                    memory_children = memory_children,
                    os_index = os_index,
                    type = type,
                    cpuset = cpuset,
                    nodeset = nodeset)
        node.__class__ = Topology
        return node
    """
    Invoke hwloc-calc to retrieve the list of children of @child_type of a topology
    object of a certain @type and @logical_index.
    @return [ dict ]
    """
    @staticmethod
    def get_children(type: str, logical_index: int, child_type: str, input_topology=None):
        cmd = 'hwloc-info'
        if input_topology is not None:
            cmd += ' --input {}'.format(input_topology)
        cmd += ' --descendants {} {}:{}'.format(child_type, type, logical_index)
        out = subprocess.getstatusoutput(cmd)
        if out[0] != 0:
            raise ValueError('Invalid topology file')
        elements = re.split('\n\w+.*\n', out[1])
        return [ Topology.parse_obj_info(e) for e in elements ]
    
    """
    Invoke hwloc-info and parse output to collect some attributes 
    of a topology object.
    @return dict
    """
    @staticmethod
    def get_node(type: str, logical_index: int, input_topology=None):
        cmd = 'hwloc-info'
        if input_topology is not None:
            cmd += ' --input {}'.format(input_topology)
        cmd += ' {}:{}'.format(type, logical_index)
        out = subprocess.getstatusoutput(cmd)
        if out[0] != 0:
            raise ValueError('Invalid topology file')
        return Topology.parse_obj_info(out[1])
    
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
    def objects(structure: bool, no_smt: bool, no_io: bool, input_topology=None):
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
    def __init__(self, structure=True, no_smt=False, no_io=True, input_topology=None):
        self.input_topology = input_topology
        objects = Topology.objects(structure, no_smt, no_io, input_topology)

        node = Topology.get_node('Machine', 0, input_topology)
        super().__init__(logical_index = node.logical_index,
                         memory_children = node.memory_children,
                         os_index = node.os_index,
                         type = node.type,
                         cpuset = node.cpuset,
                         nodeset = node.nodeset)
        
        self.special_objs = [ { 'depth': o['depth'],
                                'type': o['type'],
                                'count': o['count'], }\
                            for o in objects if o['depth'] < 0 ]

        for o in [ o for o in objects[:len(objects)] if o['depth'] > 0 ]:
            for leaf in TreeIterator(self, lambda n: n.is_leaf()):
                children = Topology.get_children(leaf.type,
                                                 leaf.logical_index,
                                                 o['type'], input_topology)
                leaf.connect_children(children)

    def get_nbobjs_by_type(self, type: str):
        return len(self.select(lambda n: n.type == type))

"Pre initialized current machine topology."
topology = Topology()

__all__ = [ 'Topology', 'topology' ]

if __name__ == '__main__':
    for i in TreeIterator(topology):
        print('{}:{} at depth {}'.format(i.type, i.logical_index, i.depth()))
