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
        node.tag = xml_node.tag
        node.attrib = xml_node.attrib
        for k,v in xml_node.attrib.items():
            # Don't override attributes
            if k in node.__dict__.keys():
                continue
            try:
                node.__dict__[k] = int(v)
            except ValueError:
                node.__dict__[k] = v
        if node.__class__ is Tree:
            node.__class__ = Topology
        return node

    def connect_children_xml(self, xml_node):
        self.children = []
        for child in list(xml_node):
            node = Topology.make_node(child)
            node.parent = self
            self.children.append(node)
            node.connect_children_xml(child)

    def __init__(self, input_topology=None,
                 structure=True, no_io=True, cpuset_only=True):
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
            
        if cpuset_only:
            self.prune(lambda n: not n.has_cpuset())

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
            return '{}'.format(self.tag)

    # Remove nodes with no cpuset.
    def has_cpuset(self):
        if hasattr(self, 'type') and self.type == 'PU':
            return True
            
        ## If no child has cpuset, then this has no cpuset.
        return next((True for c in self.children if c.has_cpuset()), False)

    def get_nbobjs_by_type(self, type: str):
        return len(self.select(lambda n: hasattr(self, 'type') and n.type == type))

    def get_obj_by_type(self, type: str, index: int, physical=False):
        if physical:
            def match(n): return hasattr(self, 'type') and n.type == type and n.os_index == index
        else:
            def match(n): return hasattr(self, 'type') and n.type == type and n.logical_index == index
        return next((TreeIterator(self, match)), None)
    
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
