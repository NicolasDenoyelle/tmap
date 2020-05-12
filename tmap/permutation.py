###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

from random import shuffle, randrange
from tree import Tree, Tleaf, TreeIterator

isindex = lambda l: next((False for i in range(len(l)) if i not in l), True)
which = lambda x, l: next((y[0] for y in zip(range(len(l)), l) if y[1] == x), None)
factorial = lambda n: n if n == 1 else n * factorial(n-1)

"""
Class representing a complete list of positive integers.
"""
class Permutation:
    """
    Build a new permutation.
    * @n: The number of elements in the permutation, if type(n) is int.
          If id is 0: the list of elements is initialized as a range.
          Else, the elements are permuted according to id. 
          Permutation(n, id).id() == id.
    * @n: A string "i:j:k:..." of a complete list of integer , if type(n) is str
    * @n: A list [i:j:k:...] of a complete list of integer , if type(n) is list.
    """
    def __init__(self, n: int, id=0):
        if isinstance(n, int):
            elements = []
            slots = [ i for i in range(n) ]
            while id > 0 and len(slots) > 0:
                s = id % len(slots)
                id = (id - s) // len(slots)
                elements.append(slots[s])
                slots = [ s for s in slots if s != elements[-1] ]
            self.elements = elements + slots
            return
        if isinstance(n, Permutation):
            self.elements = n.elements.copy()
            return
        if isinstance(n, str):
            n = [ int(i) for i in n.split(':') ]
        if isinstance(n,list):
            if not isindex(n):
                raise ValueError('Permutation elements must be a complete index.')
            self.elements = n
        else:
            raise TypeError('n must be either an index, a permutation string or a number of elements.')
        
    """
    Permutation unique id as int.
    Permutation(n, id).id() == id.
    """
    def id(self):
        ret = 0
        mul = 1 
        elements = list(range(len(self.elements)))
        for i in range(len(self.elements)):
            j = which(self.elements[i], elements)
            ret += mul * j
            mul *= len(elements)
            elements = elements[:j] + elements[j+1:]
        return ret

    def __hash__(self):
        return self.id()
        
    def __iter__(self):
        return iter(self.elements)
    
    """
    Deep copy of permutation.
    """
    def copy(self):
        p = Permutation(len(self))
        p.elements = self.elements.copy()
        return p
    
    def __getitem__(self, i: int) -> int:
        return self.elements[i]
    
    def __str__(self) -> str:
        return ':'.join([ str(i) for i in self.elements ])
    
    def __repr__(self) -> str:
        return repr(self.elements)
    
    def __len__(self) -> int:
        return len(self.elements)
    
    def __eq__(self, other) -> bool:
        if isinstance(other, list):
            return self.elements == other
        if isinstance(other, Permutation):
            return self.elements == other.elements

    """
    Associative composition law.
    Neutral: Permutation(n, 0)    
    """
    def __add__(self, p: Permutation):
        if len(p) != len(self):
            raise ValueError('Cannot add permutations of different length.')
        return Permutation(len(self), self.id() + p.id())    
    
    """
    Shuffle permutation elements.
    """
    def shuffled(self):
        ret = Permutation(len(self))
        shuffle(ret.elements)
        return ret

"""
Iterator of all permutation of a set of nelements.
"""
class PermutationIterator:
    def __init__(self, n):
        permutation = Permutation(n)
        self.id = permutation.id()
        self.n  = len(permutation)
        self.max_perm = factorial(self.n)

    def __iter__(self):
        return self

    def __next__(self):
        if self.id >= self.max_perm:
            raise StopIteration
        perm = Permutation(self.n, self.id)
        self.id += 1
        return perm

"""
A Permutation mapped on a Tree where tree leaves are permutation elements.
"""
class TreePermutation(Permutation):
    """
    Build a Permutation with as many elements as @tree_map leaves.
    if @id > 0, initialize permuation elements with a permutation of same id.
    """
    def __init__(self, tree_map: Tree, id = 0):
        self.tree = tree_map
        n = TreeIterator(tree_map, lambda n: n.is_leaf()).count()
        super().__init__(n, id)
        
    """
    Tag tree leaves with permutation elements, then sort permutation by
    shifting tree nodes based on the smallest leaf.
    return a new canonical TreePermutation.
    """
    def canonical(self):
        ret = TreePermutation(self.tree)
        i = 0
        for l in TreeIterator(ret.tree, lambda n: n.is_leaf()):
            l.tag = self.elements[i]
            i+= 1
        # This is where leaf_indexes are reordered into canonical representation.
        ret.tree.sort(by=lambda leaf: leaf.tag)
        ret.elements = [ n.tag for n in TreeIterator(ret.tree, lambda n: n.is_leaf()) ]
        return ret

    """
    Return True if the permuation is already in a canonical form.
    """
    def isCanonical(self) -> bool:
        return self.canonical() == self.elements

    """
    Return a new random canonical permutation based on this permutation.
    """
    def shuffled(self):
        ret = TreePermutation(self.tree)
        shuffle(ret.elements)
        ret.elements = ret.canonical().elements
        return ret

    """
    Return a new random, likely non canonical, permutation such that
    the canonical versions of this permutation and new permuation are equal.
    It is obtained by randomly shifting tree nodes.
    """
    def shuffled_equivalent(self):
        ret = TreePermutation(self.tree)
        ret.tree.tag_leaves()
        for node in TreeIterator(ret.tree, lambda n: not n.is_leaf()):
            ord = list(range(len(node.children)))
            shuffle(ord)
            node.swap(ord)
        ret.elements = [ self.elements[i.tag] for i in TreeIterator(ret.tree, lambda n: n.is_leaf()) ]
        return ret

"""
Iterator of all canonical permutations of a set of nelements mapped with a tree.
"""
class CanonicalPermutationIterator:
    def __init__(self, p: TreePermutation):
        self.tree = p.tree
        self.it = PermutationIterator(p)

    def __iter__(self):
        return self

    def __next__(self):
        p = TreePermutation(self.tree, next(self.it).id())
        while p != p.canonical():
            p = TreePermutation(self.tree, next(self.it).id())
        return p
    
################################################################################

__all__ = [ 'Permutation',
            'TreePermutation',
            'PermutationIterator',
            'CanonicalPermutationIterator' ]

if __name__ == '__main__':
    p = TreePermutation(Tleaf([2, 4, 2]))
    p = p.shuffled()
    print('Canonical(tree permuted) is canonical: {}'.\
          format(p.shuffled_equivalent().canonical().isCanonical()))
    n = 16
    id = randrange(n)
    print('Computed id is provided id: {}'.format(Permutation(16,id).id() == id))
    print('Neutral is neutral: {}'.format(p == p + Permutation(len(p), 0)))
    p = CanonicalPermutationIterator(TreePermutation(Tleaf([2,2])))
    print('Canonical iterator yields canonicals: {}'.\
          format(all([i.isCanonical() for i in it])))
