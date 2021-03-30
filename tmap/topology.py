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
from tmap.utils import which
from socket import gethostname
from functools import reduce

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
        node.hostname = gethostname()
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

        if input_topology is not None and input_topology[-4:] == '.xml':
            with open(input_topology) as f:
                output = f.read()
        else:
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
                    
            output = subprocess.getoutput(cmd)
        try:
            root = ElementTree.fromstring(output)
        except Exception as e:
            print("Invalid lstopo xml topology:\n{}".format(output))
            raise e

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

    def set_hostname(self, hostname):
        """
        Set attribute hostname of topology nodes to the `hostname` value.
        """
        self.hostname = hostname
        for n in self:
            n.hostname = hostname

    def get_nbobjs_by_type(self, type: str):
        return len(self.select(lambda n: hasattr(self, 'type') and n.type == type))

    def get_obj_by_type(self, type: str, index: int, physical=False):
        if physical:
            def match(n): return hasattr(self, 'type') and n.type == type and n.os_index == index
        else:
            def match(n): return hasattr(self, 'type') and n.type == type and n.logical_index == index
        return next((TreeIterator(self, match)), None)
    
    def singlify(self, level = "Machine"):
        """
        Restrict descendants of nodes with this type to a string of descendants 
        down to a single PU.
        """
        if len(self.children) == 0:
            return self
        if hasattr(self, 'type') and self.type == level:
            self.children = [ next(c for c in self.children if c.has_cpuset()) ]
            self.children[0].singlify(level = self.children[0].type)
        else:
            for n in self.children:
                n.singlify(level)
        return self

    def flatten(self):
        """
        Cut nodes between root and leaves with an arity of 1.
        """
        e = next((n for n in self if n.arity()==1), None)
        while e is not None:
            e.remove_depth(1)
            e = next((n for n in self if n.arity()==1), None)
        return self

    def split(self, n=2):
        """
        Split a node into several nodes, adding a level to the tree.
        """
        if len(self.children) % n != 0:
            raise ValueError('Level {} can only be split into a divisor of its arity ({})'.format(repr(self), len(self.children)))
        num = len(self.children) // n
        children = [ self.children[i:i+num] for i in range(0, len(self.children), num) ]
        self.children = []
        children = [ Tree(self, c) for c in children ]
        return self

    def split_type(self, level_type, n=2):
        """
        Split all node of given type when possible.
        """
        nodes = list(TreeIterator(self,
                                  lambda node: hasattr(node, 'type') and \
                                  node.type == level_type))
        for node in nodes:
            try:
                node.split(n)
            except ValueError:
                print("Node {} could not be split in {}".format(repr(node), n))
                pass
        return self

    def remove_depth(self, depth):
        """
        Remove all nodes at depth depth and connect their children to their
        parent.
        """
        depth += self.get_depth()
        if depth <= 0:
            return self
        parents = [ n for n in self if n.get_depth() == depth-1 ]
        for p in parents:
            children = reduce(lambda x, y: x+y, [ c.children for c in p.children ], [])
            p.children = []
            p.connect_children(children)
            p.PUs = reduce(lambda x, y: x+y, [ c.PUs for c in children ], [])
        return self

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
