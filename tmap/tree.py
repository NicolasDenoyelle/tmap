###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

from functools import reduce

unlist = lambda l: [l] if type(l) is not list else \
         reduce(lambda x, y: \
                (unlist(x) if type(x) is list else [x]) + \
                (unlist(y) if type(y) is list else [y]), l, [])
argmin = lambda l: min(zip(l, range(len(l))))[1]
which = lambda x, l: next((y[0] for y in zip(range(len(l)), l) if y[1] == x), None)
order = lambda l: [ x[1] for x in sorted(zip(l, range(len(l)))) ]
isindex = lambda l: next((False for i in range(len(l)) if i not in l), True)

"""
Tree container abstraction:
A tree and a tree node are same objects. 
The container is built recursively. Therefore, all Tree methods should work 
on all tree nodes.
Nodes contain a link to the parent and a list of children plus 
some user defined attributes.
"""
class Tree:
    """
    Tree node constructor.
    At this step, it is possible to provide @parent and @children.
    It is also possible to do it later via connect_children() and connect_parent().
    Additional keyword arguments are set as attributes of the node.
    """
    def __init__(self, parent=None, children=None, **kwargs):
        self.parent = parent
        self.children = [] if children is None else children
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return str(self.coords())

    def __str__(self):
        s = ""
        depth = self.max_depth()
        for n in self:
            coords = n.coords()
            if len(coords) == 0:
                continue
            for i in range(len(coords)-1):
                s += ('|' if coords[i] != 0 else ' ') + (' ' * (i+1) * 3)
            s += '+' + ('-'*len(coords)*3) + '{}\n'.format(repr(n))
            if n != n.parent.children[-1]:
                for i in range(len(coords)-1):
                    s += ('|' if coords[i] != 0 else ' ') + (' ' * (i+1) * 3)
                s += '|' + ' ' * (len(coords)*3 + 3) + '\n'
        return s

    "Iterate the tree as per TreeIterator walk."
    def __iter__(self):
        return TreeIterator(self)

    """
    Build links from this nodes to children and from children to this node.
    @children can be a list of args, an array of Tree or a Tree.
    """
    def connect_children(self, *args):
        if isinstance(args[0], Tree):
            c = [ args[0] ]
        elif isinstance(args[0], list):
            c = args[0]
        else:
            c = list(args)
        for i in c:
            if not isinstance(i, Tree):
                raise ValueError('Connect children takes Tree arguments')
            i.parent = self
            self.children.append(i)

    """
    Build links from parent to this node and from this node to parent.
    @p must be a Tree.
    """
    def connect_parent(self, p):
        if not isinstance(p, Tree):
            raise ValueError('Connect parent takes Tree argument')
        p.children.append(self)
        self.parent = p

    "Return True if this node is the Tree root node"
    def is_root(self) -> bool:
        return self.parent == None

    "Return True if this node is a leaf of the Tree"
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    "Compute recursively this node leaf"
    def depth(self) -> int:
        if self.parent is None:
            return 0
        return 1 + self.parent.depth()
    
    "Return node arity"
    def arity(self):
        return len(self.children)
    
    "Compute recursively maximum distance to a leaf from this node"
    def max_depth(self) -> int:
        return max([ l.depth() for l in TreeIterator(self, lambda n: n.is_leaf()) ])
    
    """
    Retrieve a descendant node by its relative coordinates to this node.
    @coord is a list of int. It does not includes this node coord: 0.
    """
    def __getitem__(self, coords: list):
        if len(coords) == 0:
            return self
        if len(self.children) == 0:
            return self
        if len(coords) == 1:
            return self.children[coords[0]]
        else:
            return self.children[coords[0]][coords[1:]]
    
    """
    Get the coordinate of this node.
    """
    def coords(self) -> list:
        if self.parent is None:
            return []
        return self.parent.coords() + [ which(self, self.parent.children) ]
    
    """
    Reorder children of this node.
    The function checks that the provided index is suitable for the operation.
    """
    def swap(self, order: list):
        if len(order) != len(self.children) or not isindex(order):
            raise ValueError('swap order of Tree children must contain complete index')
        self.children = [ self.children[i] for i in order ]
        
    """
    Get index of this node in parent list.
    """
    def index(self):
        if self.parent is None:
            return 0
        return which(self, self.parent.children)
    
    """
    Get the root of the Tree containing this node.
    """
    def root(self):
        if self.parent is None:
            return self
        return self.parent.root()
    
    """
    Add an attribute "tag" to the leaves of this node containing the leaf index
    in a round-robin order.
    """
    def tag_leaves(self):
        i = 0
        for l in TreeIterator(self, lambda n: n.is_leaf()):
            l.tag = i
            i += 1
            
    """
    Get all nodes at depth @i from this node.
    """
    def level(self, i: int) -> list:
        if i == 0 or self.is_leaf():
            return [ self ]
        return unlist([ n.level(i-1) for n in self.children ])
    
    """
    Apply recursively a function to this node and all its descendants.
    """
    def apply(self, fn = lambda node: node, depth=-1):
        fn(self)        
        if depth == 0 or self.is_leaf():            
            return
        for c in self.children:
            c.apply(fn, depth-1)

    """
    Recursively reduce a list of nodes to a single node.
    """
    def reduce(self, fn = lambda nodes: nodes[0]):
        if self.is_leaf():
            return self
        else:
            return fn([ n.reduce(fn) for n in self.children ])
    
    """
    Walk all nodes of the tree and return nodes satisfying cond.
    """
    def select(self, cond = lambda n: True):
        return [ n for n in self if cond(n) ]
        
    """
    Return the right-most leaf of the tree.
    """
    def last_leaf(self):
        if self.is_leaf():
            return self
        return self.children[-1].last_leaf()

    """
    Return the left-most leaf of the tree.
    """
    def first_leaf(self):
        if self.is_leaf():
            return self
        return self.children[0].first_leaf()
    
    def sort(self, by=lambda leaf: leaf.tag):
        # For every children get min leaf by tag
        mins = [ by(c.reduce(lambda nodes: \
                          nodes[argmin([ by(node) for node in nodes ])])) \
                 for c in self.children ]
        # Reorder children by min leaf
        self.swap(order(mins))
        # Run recursively on children
        for c in self.children:
            c.sort()
    
    """
    Prune a node of the tree.
    @param cond provides a condition on a node for elimination.
    if cond modified and does not eliminate this node, the tree
    is walked recursively to eliminate decendants based on cond.
    """
    def prune(self, cond=lambda n: True):
        eliminated = [ n for n in self if cond(n) ]
        for e in eliminated:
            if e.parent is not None:
                e.parent.children = [ c for c in e.parent.children if c != e ]
        return eliminated

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
class TreeIterator:
    """
    Create an iterator of @tree nodes.
    You can optionnally filter nodes returned.
    For instance you can return a leaf iterator with:
    TreeIterator(tree, lambda n: n.is_leaf())
    """
    def __init__(self, tree, cond = lambda node: True):
        self.tree = tree
        self.cond = cond
        self.reset()

    """
    Iterate through all elements and return the number of elements
    """
    def count(self, start = 0):
        try:
            next(self)
            return self.count(start+1)
        except StopIteration:
            return start

    """
    Reset iterator without creating a new iterator.
    """
    def reset(self):
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
class ScatterTreeIterator:
    """
    Create an iterator of @tree nodes.
    You can optionnally filter nodes returned.
    For instance you can return a leaf iterator with:
    ScatterTreeIterator(tree, lambda n: n.is_leaf())
    """
    def __init__(self, tree, cond = lambda node: True):
        self.tree = tree
        self.stop = False
        self.cond = cond
        for node in tree:
            node.visit = -2
            
    def __iter__(self):
        return self

    """
    Iterate through all elements and return the number of elements
    """
    def count(self, start = 0):
        try:
            next(self)
            return self.count(start+1)
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

"""
Build a Tleaf type tree.
A Tleaf is a tree where all nodes at same depth have the same arity.
"""
class Tleaf(Tree):
    """
    Tleaf constructor.
    @arities: a list of arity per level above leaves. (Does not include the last [1])
    """
    def __init__(self, arities):
        super().__init__()        
        if len(arities) > 1:
            self.connect_children([ Tleaf(arities[1:]) for i in range(arities[0])])
        elif len(arities) == 1:
            self.connect_children([ Tleaf([]) for i in range(arities[0])])
        self.tag_leaves()
        self.arities = arities

################################################################################

__all__ = [ 'Tree',
            'Tleaf',
            'TreeIterator',
            'ScatterTreeIterator' ]

if __name__ == '__main__':
    tleaf = Tleaf([2,4,2])
    print([ n.index() for n in TreeIterator(tleaf, lambda n: n.is_leaf()) ])
    print([ n.tag for n in TreeIterator(tleaf, lambda n: n.is_leaf()) ])
    
    node = tleaf[[1,3,1]]
    node.coords()
    
    tleaf.swap([1,0])
    tleaf[[1]].swap([1,0,3,2])
    print([ n.tag for n in TreeIterator(tleaf, lambda n: n.is_leaf()) ])
    tleaf.sort()
    print([ n.tag for n in TreeIterator(tleaf, lambda n: n.is_leaf()) ])
    for i in ScatterTreeIterator(tleaf, cond= lambda node: node.is_leaf()):
        print('{}'.format(i.coords()))
    print(tleaf)
    
    tleaf.prune(lambda n: n.is_leaf() and n.coords()[-1] == 0)
    print(tleaf)
