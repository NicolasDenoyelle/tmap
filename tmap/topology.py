###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

from tmap.tree import Tree, TreeIterator
from tmap.permutation import TreePermutation
from xml.etree import ElementTree
import subprocess
import re
import os
from copy import deepcopy

hwloc_version=None
s, out = subprocess.getstatusoutput('hwloc-info --version')
if s == 0:
    hwloc_version = re.match('.*(?P<i>\d[.]\d[.]\d).*',out)
if hwloc_version is not None:
    hwloc_version = [ int(i) for i in hwloc_version.group(1).split('.') ]

class Topology(Tree):
    """
    Use lstopo command line utility to generate topology xml then parse xml to build a topology.
    """

    @staticmethod
    def make_node(xml_node, node=None):
        if node is None:
            node = Tree()
        node.attrib = xml_node.attrib
        for k,v in xml_node.attrib.items():
            try:
                node.__dict__[k] = int(v)
            except ValueError:
                node.__dict__[k] = v
        node.special_children = []
        if node.__class__ is Tree:
            node.__class__ = Topology
        return node

    def connect_children_xml(self, xml_node):
        self.children = []
        for child in xml_node.getchildren():
            node = Topology.make_node(child)
            node.parent = self
            if hasattr(node, 'cpuset') and not hasattr(node, 'local_memory'):
                self.children.append(node)
                node.connect_children_xml(child)
            else:
                self.special_children.append(node)

    def __init__(self, structure=True, no_io=True, input_topology=None):
        """
        Topology Tree constructor.
        If structure is True, topology is filtered to keep objects important for 
        the structure.
        If no_io is True, io objects are filtered.
        """
        
        cmd = 'lstopo --of xml'
        if input_topology is not None:
            if os.path.isfile(os.path.expanduser(input_topology)):
                cmd += ' --input {}'.format(input_topology)
            else:
                cmd += ' --input "{}"'.format(input_topology)
        if structure:
            cmd += ' --filter all:structure'
        if no_io:
            cmd += ' --no-io'            
        root = ElementTree.fromstring(subprocess.getoutput(cmd))
        # Initialize root
        super().__init__(logical_index=0)
        Topology.make_node(root, self)
        # Connect childrens recursively
        self.connect_children_xml(root)
        
        # Set logical indexes:
        types = set([ n.type for n in self if hasattr(n, 'type') ])
        for t in types:
            nodes = [ n for n in self if hasattr(n, 'type') and n.type == t ]
            for n, i in zip(nodes, range(len(nodes))):
                n.logical_index = i

        # Set list of child PUs:
        for n in self:
            n.PUs = []
            for PU in n:
                if PU.is_leaf():
                    n.PUs.append(PU)

    def __repr__(self):
        if hasattr(self, 'type'):
            return '{}:{}'.format(self.type, self.logical_index)
        else:
            return '{}:{}'.format(next(iter(self.attrib)))

    def get_nbobjs_by_type(self, type: str):
        return len(self.select(lambda n: n.type == type))

    def get_obj_by_type(self, type: str, index: int, physical=False):
        if physical:
            def match(n): return n.type == type and n.os_index == index
        else:
            def match(n): return n.type == type and n.logical_index == index
        return next((TreeIterator(self, match)), None)

    def restrict(self, indexes: list, type: str):
        # Prune nodes in index.
        eliminated = self.prune(
            lambda n: hasattr(n, 'type') and n.type == type and n.logical_index not in indexes)
        elimination = [e.parent for e in eliminated if e.parent.arity() == 0]
        if len(elimination) > 0:
            next_type = next(iter(elimination)).type
            next_indexes = [
                n.logical_index for n in self
                if n.type == next_type and n not in elimination
            ]
            return self.restrict(next_indexes, next_type)
        return self

    def singlify(self, level = "Machine"):
        nodes = [ n for n in self if hasattr(n, 'type') and n.type == level ]
        def singlify_node(node):
            if len(node.children) > 0:
                node.children = [node.children[0]]
        for node in nodes:
            node.apply(singlify_node)

    def dup(self):
        return deepcopy(self)

"Pre initialized current machine topology."
if hwloc_version is not None:
    topology = Topology()
    __all__ = ['hwloc_version', 'topology', 'Topology']
else:
    __all__ = ['hwloc_version', 'Topology']

if __name__ == '__main__':
    t = Topology()
    print(t)
    t.restrict([0, 1], 'PU')
    print(t)
