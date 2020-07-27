###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import sys
from random import shuffle, randint
from tmap.tree import Tree, Tleaf, TreeIterator
from tmap.utils import isindex, which, factorial

class Permutation:
    """
    Class representing a complete list of positive integers.
    """

    def __init__(self, n: int, id=0):
        """
        Build a new permutation.
        * @n: The number of elements in the permutation, if type(n) is int.
          If id is 0: the list of elements is initialized as a range.
          Else, the elements are permuted according to id. 
          Permutation(n, id).id() == id.
        * @n: A string "i:j:k:..." of a complete list of integer , 
        if type(n) is str
        * @n: A list [i:j:k:...] of a complete list of integer , 
        if type(n) is list.
        """

        if isinstance(n, int):
            self.max_id = factorial(n)
            id = id % self.max_id
            elements = []
            slots = [i for i in range(n)]
            while id > 0 and len(slots) > 0:
                s = id % len(slots)
                id = (id - s) // len(slots)
                elements.append(slots[s])
                slots = [s for s in slots if s != elements[-1]]
            self.elements = elements + slots
            return
        if isinstance(n, Permutation):
            self.elements = n.elements.copy()
            self.max_id = factorial(len(self.elements))
            return
        if isinstance(n, str):
            n = [int(i) for i in n.split(':')]
            self.max_id = factorial(len(n))
        if isinstance(n, list):
            if not isindex(n):
                raise ValueError(
                    'Permutation elements must be a complete index.')
            self.elements = n
            self.max_id = factorial(len(n))
        else:
            raise TypeError("""n must be either an index, a permutation string
            or a number of elements.""")        

    def id(self):
        """
        Permutation unique id as int.
        Permutation(n, id).id() == id.
        """

        ret = 0
        mul = 1
        elements = list(range(len(self.elements)))
        for i in range(len(self.elements)):
            j = which(elements, lambda x: x==self.elements[i])
            ret += mul * j
            mul *= len(elements)
            elements = elements[:j] + elements[j + 1:]
        return ret

    def __hash__(self):
        return self.id()

    def __iter__(self):
        return iter(self.elements)

    def copy(self):
        """
        Deep copy of permutation.
        """

        p = Permutation(len(self))
        p.elements = self.elements.copy()
        return p

    def __getitem__(self, i: int) -> int:
        return self.elements[i]

    def __str__(self) -> str:
        return ':'.join([str(i) for i in self.elements])

    def __repr__(self) -> str:
        return repr(self.elements)

    def __len__(self) -> int:
        return len(self.elements)

    def __eq__(self, other) -> bool:
        if isinstance(other, list):
            return self.elements == other
        if isinstance(other, Permutation):
            return self.elements == other.elements

    def __add__(self, p):
        """
        Associative composition law.
        Neutral: Permutation(n, 0)    
        """

        if len(p) != len(self):
            raise ValueError('Cannot add permutations of different length.')
        id_max = factorial(len(p))
        new_id = (self.id() + p.id()) % id_max
        return Permutation(len(self), new_id)

    def shuffled(self):
        """
        Shuffle permutation elements.
        """

        ret = Permutation(len(self))
        shuffle(ret.elements)
        return ret

class PermutationIterator:
    """
    Iterator of all permutation of a set of nelements.
    """

    def __init__(self, n):
        if isinstance(n, int):
            permutation = Permutation(n)
        elif isinstance(n, Permutation):
            permutation = n
        self.i = permutation.id()
        self.len = len(permutation)
        self.max = permutation.max_id

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= self.max:
            raise StopIteration
        perm = Permutation(self.len, self.i)
        self.i += 1
        return perm


class TreePermutation(Permutation):
    """
    A Permutation mapped on a Tree where tree leaves are permutation elements.
    """

    def __init__(self, tree_map: Tree, id=0):
        """
        Build a Permutation with as many elements as @tree_map leaves.
        if @id > 0, initialize permutation elements with a permutation of same id.
        """
        self.tree = tree_map
        n = TreeIterator(tree_map, lambda n: n.is_leaf()).count()
        super().__init__(n, id)

    def canonical(self):
        """
        Tag tree leaves with permutation elements, then sort permutation by
        shifting tree nodes based on the smallest leaf.
        return a new canonical TreePermutation.
        """

        ret = TreePermutation(self.tree)
        i = 0
        for l in TreeIterator(ret.tree, lambda n: n.is_leaf()):
            l.tag = self.elements[i]
            i += 1
        # This is where leaf_indexes are reordered into canonical
        # representation.
        ret.tree.sort(by=lambda leaf: leaf.tag)
        ret.elements = [
            n.tag for n in TreeIterator(ret.tree, lambda n: n.is_leaf())
        ]
        return ret

    def is_canonical(self) -> bool:
        """
        Return True if the permutation is already in a canonical form.
        """
        return self.canonical() == self.elements

    def shuffled(self):
        """
        Return a new random canonical permutation based on this permutation.
        """

        ret = TreePermutation(self.tree)
        shuffle(ret.elements)
        ret.elements = ret.canonical().elements
        return ret

    def shuffled_equivalent(self):
        """
        Return a new random, likely non canonical, permutation such that
        the canonical versions of this permutation and new permutation are equal.
        It is obtained by randomly shifting tree nodes.
        """

        ret = TreePermutation(self.tree)
        ret.tree.tag_leaves()
        for node in TreeIterator(ret.tree, lambda n: not n.is_leaf()):
            ord = list(range(len(node.children)))
            shuffle(ord)
            node.swap(ord)
        ret.elements = [
            self.elements[i.tag]
            for i in TreeIterator(ret.tree, lambda n: n.is_leaf())
        ]
        return ret


class CanonicalPermutationIterator:
    """
    Iterator of all canonical permutations of a set of nelements mapped 
    with a tree.
    """

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

__all__ = [
    'Permutation', 'TreePermutation', 'PermutationIterator',
    'CanonicalPermutationIterator'
]

################################################################################
# Testing                                                                      #
################################################################################

import unittest

class TestPermutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        trials = 20
        size_min = 4
        size_max = 256
        sizes = [ randint(size_min, size_max) for i in range(trials) ]
        cls.ids = [ randint(0, factorial(s)) for s in sizes ]
        cls.permutations = [ Permutation(size, id) \
                             for size, id in zip(sizes, cls.ids) ]
    
    def test_copy(self):        
        for permutation in self.permutations:
            copy = permutation.copy()
            self.assertEqual(copy, permutation)
            self.assertNotEqual(copy.shuffled(), permutation)
        
    def test_id(self):
        for id, permutation in zip(self.ids, self.permutations):
            # assert permutation built by id yields the same id.
            self.assertEqual(id, permutation.id())
            # assert that shuffled permutation id will build the same
            # permutation 
            shuffled = permutation.shuffled()
            permutation = Permutation(len(permutation), shuffled.id())
            self.assertEqual(shuffled, permutation)

    def test_add(self):
        for permutation in self.permutations:
            other = Permutation(len(permutation), randint(0, sys.maxsize))
            self.assertEqual((other + permutation).id(),
                             (permutation.id() + other.id()) % permutation.max_id)

class TestPermutationIterator(unittest.TestCase):
    def test_iterator(self):
        size = 5
        permutation = Permutation(size)
        tot = sum([ 1 for i in PermutationIterator(permutation) ])
        self.assertEqual(tot, permutation.max_id)

class TestTreePermutation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        trials = 20
        arity_max = 5
        arity_min = 2
        depth_min = 2
        depth_max = 4
        arities = []
        for i in range(trials):
            arities.append([ randint(arity_min, arity_max) \
                             for i in range(randint(depth_min, depth_max)) ])
        trees = [ Tleaf(a) for a in arities ]
        cls.permutations = [ TreePermutation(t).shuffled() for t in trees ]
        
    def test_canonical(self):
        for permutation in self.permutations:
            canonical = permutation.canonical()
            self.assertTrue(canonical.is_canonical())
            equivalent = permutation.shuffled_equivalent()            
            self.assertEqual(equivalent.canonical(), canonical)

    def test_canonical_iterator(self):
        it = CanonicalPermutationIterator(TreePermutation(Tleaf([2, 2])))
        self.assertTrue(all([i.is_canonical() for i in it]))
            
if __name__ == '__main__':
    unittest.main()
