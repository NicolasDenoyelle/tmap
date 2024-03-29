###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

from random import randint
from tmap.utils import concat, which, isindex

class Tree:
    """
    Tree container abstraction:
    A tree and a tree node are same objects. 
    The container is built recursively. Therefore, all Tree methods should work 
    on all tree nodes.
    Nodes contain a link to the parent and a list of children plus 
    some user defined attributes.
    """
    
    def __init__(self, parent=None, children=None, **kwargs):
        """
        Tree node constructor.
        At this step, it is possible to provide @parent and @children.
        It is also possible to do it later via connect_children() and connect_parent().
        Additional keyword arguments are set as attributes of the node.
        """

        self.parent = parent
        if parent is not None:
            parent.children.append(self)
        self.children = [] if children is None else children
        for c in self.children:
            c.parent = self            
        for k, v in kwargs.items():
            setattr(self, k, v)

    def from_list(l):
        t = Tree()
        if isinstance(l, list):
            kids = [ Tree.from_list(x) for x in l ]
        elif isinstance(l, int):
            kids = [ Tree() for i in range(l) ]
        else:
            kids = [ Tree(attr=l) ]
        if len(kids) > 0:
            t.connect_children(kids)
        return t

    def __repr__(self):
        return str(self.coords())

    def __str__(self):
        """
        Output multiline nice tree representation where nodes are repr(node) 
        """
        s = ""
        depth = self.max_depth()
        for n in self:
            coords = n.coords()
            if len(coords) == 0:
                continue
            for i in range(len(coords) - 1):
                s += ('|' if coords[i] != 0 else ' ') + (' ' * (i + 1) * 3)
            s += '+' + ('-' * len(coords) * 3) + '{}\n'.format(repr(n))
            if n != n.parent.children[-1]:
                for i in range(len(coords) - 1):
                    s += ('|' if coords[i] != 0 else ' ') + (' ' * (i + 1) * 3)
                s += '|' + ' ' * (len(coords) * 3 + 3) + '\n'
        return s

    def __iter__(self):
        """
        Iterate the tree as per TreeIterator walk.
        """
        return TreeIterator(self)

    def is_equal(self, other):
        return next((False for a,b in zip(iter(self), iter(other)) if a.arity() != b.arity()), True)

    def connect_children(self, *args):
        """
        Build links from this nodes to children and from children to this node.
        @children can be a list of args, an array of Tree or a Tree.
        """

        if isinstance(args[0], Tree):
            c = [args[0]]
        elif isinstance(args[0], list):
            c = args[0]
        else:
            c = list(args)
        for i in c:
            if not isinstance(i, Tree):
                raise ValueError('Connect children takes Tree arguments')
            i.parent = self
            self.children.append(i)

    def connect_parent(self, p):
        """
        Build links from parent to this node and from this node to parent.
        @p must be a Tree.
        """
        
        if not isinstance(p, Tree):
            raise ValueError('Connect parent takes Tree argument')
        p.children.append(self)
        self.parent = p

    def is_root(self) -> bool:
        """
        Return True if this node is the Tree root node
        """
        return self.parent == None

    def is_leaf(self) -> bool:
        """
        Return True if this node is a leaf of the Tree
        """
        return len(self.children) == 0

    def get_depth(self) -> int:
        """
        Compute recursively this node leaf
        """
        if self.parent is None:
            return 0
        return 1 + self.parent.get_depth()

    def arity(self):
        """
        Return node arity
        """
        return len(self.children)

    def max_depth(self) -> int:
        """
        Compute recursively maximum distance to a leaf from this node
        """
        return max(
            [l.get_depth() for l in TreeIterator(self, lambda n: n.is_leaf())])

    def __getitem__(self, coords: list):
        """
        Retrieve a descendant node by its relative coordinates to this node.
        @coord is a list of int. It does not includes this node coord: 0.
        """
        
        if len(coords) == 0:
            return self
        if len(self.children) == 0:
            return self
        if len(coords) == 1:
            return self.children[coords[0]]
        else:
            return self.children[coords[0]][coords[1:]]

    def coords(self) -> list:
        """
        Get the coordinate of this node.
        """
        
        if self.parent is None:
            return []
        return self.parent.coords() + [which(self.parent.children, lambda x: x==self)]

    def swap(self, index: list):
        """
        Reorder a subset children of this node.
        """
        children = [ self.children[i] for i in index ]
        for c, i in zip([ self.children[i] for i in index ], sorted(index)):
            self.children[i] = c

    def index(self):
        """
        Get index of this node in parent list.
        """
        if self.parent is None:
            return 0
        return which(self.parent.children, lambda x: x==self)

    def root(self):
        """
        Get the root of the Tree containing this node.
        """
        
        if self.parent is None:
            return self
        return self.parent.root()

    def level(self, i: int) -> list:
        """
        Get all nodes at depth @i from this node.
        """
        if i == 0:
            return [ self ]
        if self.is_leaf():
            return []
        return concat([ n.level(i - 1) for n in self.children ])

    def apply(self, fn=lambda node: node, depth=-1):
        """
        Apply recursively a function to this node and all its descendants.
        """
        fn(self)
        if depth == 0 or self.is_leaf():
            return
        for c in self.children:
            c.apply(fn, depth - 1)

    def reduce(self, fn=lambda nodes: nodes[0]):
        """
        Select a leaf by recursive reduction choice.
        """
        if self.is_leaf():
            return self
        else:
            return fn([n.reduce(fn) for n in self.children])

    def select(self, cond=lambda n: True):
        """
        Walk all nodes of the tree and return nodes satisfying cond.
        """
        return [n for n in self if cond(n)]

    def last_leaf(self):
        """
        Return the right-most leaf of the tree.
        """
        if self.is_leaf():
            return self
        return self.children[-1].last_leaf()

    def first_leaf(self):
        """
        Return the left-most leaf of the tree.
        """
        if self.is_leaf():
            return self
        return self.children[0].first_leaf()

    def remove(self):
        """
        Remove a node from the tree and connect its children instead of itself 
        to the parent.
        """
        if self.parent is not None:
            self.parent.children = [ n for n in self.parent.children if n != self ]
            self.parent.children += self.children
        for c in self.children:
            c.parent = self.parent
        return self

    def remove_depth(self, depth):
        """
        Remove all nodes at depth depth and connect their children to their
        parent.
        """
        depth += self.get_depth()
        if depth <= 0:
            return self
        root = self.root()
        nodes = [ n for n in root if n.get_depth() == depth ]
        for n in nodes:            
            n.remove()
        return self
    
    def prune(self, cond=lambda n: True):
        """
        Prune a node and/or its children from a tree.
        @param cond provides a condition on a node for elimination.
        if cond is modified and does not eliminate this node, the tree
        is walked recursively to eliminate decendants based on cond.
        """

        eliminated = [n for n in self if cond(n)]
        for e in eliminated:
            if e.parent is not None:
                e.parent.children = [c for c in e.parent.children if c != e]
        return eliminated

class TreeIterator:
    """
    Iterator on all nodes of the tree
    with the following order:
    6----5----4
    |    |
    |    +----3
    |
    +----2----1
      |
      +----0
    """
    
    def __init__(self, tree, cond=lambda node: True):
        """
        Create an iterator of @tree nodes.
        You can optionnally filter nodes returned.
        For instance you can return a leaf iterator with:
        TreeIterator(tree, lambda n: n.is_leaf())
        """
        
        self.tree = tree
        self.cond = cond
        self.reset()

    def count(self, start=0):
        """
        Iterate through all elements and return the number of elements
        """
        
        try:
            next(self)
            return self.count(start + 1)
        except StopIteration:
            return start

    def reset(self):
        """
        Reset iterator without creating a new iterator.
        """

        self.current = self.tree
        while len(self.current.children) > 0:
            self.current = self.current.children[0]

    def __iter__(self):
        return self

    def __next__(self):
        if self.current is None:
            raise StopIteration
        ret = self.current
        n = self.current.index() + 1
        if self.current.parent is None or self.current is self.tree:
            self.current = None
        elif n == len(self.current.parent.children):
            self.current = self.current.parent
        else:
            self.current = self.current.parent.children[n]
            while len(self.current.children) > 0:
                self.current = self.current.children[0]
        return ret if self.cond(ret) else next(self)

class ScatterTreeIterator:
    """
    Iterator on all nodes of the tree
    with the following order:
    0----2----6
    |    |
    |    +----4
    |
    +----1----5
      |
      +----3
    """
    
    def __init__(self, tree, cond=lambda node: True):
        """
        Create an iterator of @tree nodes.
        You can optionnally filter nodes returned.
        For instance you can return a leaf iterator with:
        ScatterTreeIterator(tree, lambda n: n.is_leaf())
        """
        
        self.tree = tree
        self.stop = False
        self.cond = cond
        for node in tree:
            node.visit = -2

    def __iter__(self):
        return self

    def count(self, start=0):
        """
        Iterate through all elements and return the number of elements
        """
        
        try:
            next(self)
            return self.count(start + 1)
        except StopIteration:
            return start

    def _visit_node_(self, node):
        node.visit = node.visit + 1
        if node.visit < 0:
            return node
        if node.visit < len(node.children):
            return self._visit_node_(node.children[node.visit])
        else:
            node.visit = -1
            if node == self.tree.last_leaf():
                raise StopIteration()
            return self._visit_node_(self.tree)

    def __next__(self):
        ret = self._visit_node_(self.tree)
        return ret if self.cond(ret) else next(self)

class Trandom(Tree):
    """
    Random tree generator
    """                
    def __init__(self, arity_max = 3, depth_min = 2, depth_max = 3, rdgen=randint):
        super().__init__()
        self.gen_children(arity_max, 2, depth_min-1, depth_max-1, rdgen)

    def gen_children(self, arity_max, arity_min, depth_min, depth_max, rdgen):
        if depth_min > 0:
            children = [ Tree() for i in range(rdgen(arity_min, arity_max)) ]
            self.connect_children(children)
            for c in children:
                c.__class__ = Trandom
                c.gen_children(arity_max, arity_min, depth_min-1, depth_max, rdgen)
        elif depth_max > 0:
            children = [ Tree() for i in range(rdgen(0, arity_max)) ]
            self.connect_children(children)
            for c in children:
                c.__class__ = Trandom
                c.gen_children(arity_max, arity_min, depth_min, depth_max-1, rdgen)
        
class Tleaf(Tree):
    """
    Build a Tleaf type tree.
    A Tleaf is a tree where all nodes at same depth have the same arity.
    """

    def __init__(self, arities, *args):
        """
        Tleaf constructor.
        @arities: a list of arity per level above leaves.
        @arities can also be one level followed by @*args other levels.
        """
        
        super().__init__()

        if isinstance(arities, int):
            arities = [ arities ] + list(args)
        if len(arities) > 1:
            self.connect_children(
                [Tleaf(arities[1:]) for i in range(arities[0])])
        elif len(arities) == 1:
            self.connect_children([Tleaf([]) for i in range(arities[0])])
        self.arities = arities

__all__ = ['Tree', 'Tleaf', 'Trandom', 'TreeIterator', 'ScatterTreeIterator']

################################################################################
# Testing                                                                      #
################################################################################

import unittest

class TestTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trees = [ Trandom() for i in range(4) ]

    def test_root(self):
        for tree in self.trees:
            for node in tree:
                self.assertEqual(node.root(), tree)
                
    def test_coords(self):
        for tree in self.trees:
            for node in tree:
                coords = node.coords()
                while node.parent is not None:
                    self.assertEqual(coords[-1], node.index())
                    coords = coords[:-1]
                    node = node.parent

    def test_depth(self):
        for tree in self.trees:
            depth = tree.max_depth()
            for node in tree:
                node_depth = node.get_depth()
                self.assertTrue(node_depth <= depth)
                for i in range(node_depth):
                    self.assertTrue(node.parent is not None)
                    node = node.parent

    def test_level(self):
        for tree in self.trees:
            for i in range(tree.max_depth()):
                level = tree.level(i)
                for l in level:
                    self.assertEqual(l.get_depth(), i)

    def test_reduce(self):
        for tree in self.trees:
            first_leaf = tree.reduce(lambda nodes: nodes[0])
            self.assertTrue(first_leaf.is_leaf())
            self.assertEqual(sum(first_leaf.coords()), 0)

    def test_iterator(self):
        for tree in self.trees:
            it = TreeIterator(tree)
            prev = next(it)
            for node in it:
                prev_coords = prev.coords()
                node_coords = node.coords()
                self.assertTrue(prev_coords < node_coords or
                                len(prev_coords) > len(node_coords))
                prev = node

    def test_prune(self):
        for tree in self.trees:
            for node in tree:
                if 2 in node.coords():
                    node.marked = True
                else:
                    node.marked = False
            tree.prune(cond=lambda n: n.marked)
            self.assertTrue(all([not n.marked for n in tree]))

if __name__ == '__main__':
    unittest.main()
