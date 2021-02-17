###############################################################################
# Copyright 2020 UChicago Argonne, LLC.
# (c.f. AUTHORS, LICENSE)
#
# For more info, see https://github.com/NicolasDenoyelle/tmap
#
# SPDX-License-Identifier: BSD-3-Clause
##############################################################################

import sys
from copy import deepcopy
from random import shuffle, randint
from functools import reduce
from tmap.tree import Tree, Tleaf, TreeIterator
from tmap.utils import isindex, which, factorial, order

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
        * @n: A list [i:j:k:...] of a complete list of integer ,
        if type(n) is list.
        * @id: A big int representing the permutation id.
        * @id: A string "P\x1a\n+õûáö\x83ïo%&U\x8b[5´d" representing the permutation hash.
        """

        # Make sure id is an integer.
        if isinstance(id, str):
            i = 0
            for b in bytes(id, "latin1"):
                i = i << 8
                i = i | b
            id = i
        if not isinstance(id, int):
            raise ValueError("Expected 'int' of 'str' for id.")
        
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
        return deepcopy(self)

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

    def shuffle(self):
        """
        Shuffle permutation elements.
        """
        shuffle(self.elements)
        return self

    def inverse(self):
        """
        Get the inverse permutation of this permutation.
        """
        ret = self.copy()
        ret.elements = order(ret.elements)
        return ret        

    @staticmethod
    def transform(src, dst):
        """
        Build a permutation that reorder src into dst.        
        """
        return Permutation([ next(i for (i,s) in zip(range(len(src)), src) if s == d) for d in dst ])

class TreePermutation(Permutation):
    """
    A Permutation mapped on a Tree where tree leaves are permutation elements.
    """            
    def __init__(self, tree_map: Tree, *args, **kwargs):
        """
        Build a Permutation with as many elements as @tree_map leaves.
        if @id > 0, initialize permutation elements with a permutation of same id.
        """
        self.tree = tree_map
        n = TreeIterator(tree_map, lambda n: n.is_leaf()).count()
        if len(args) == 0 and len(kwargs.items()) == 0:
            super().__init__(n)
        else:
            super().__init__(*args, **kwargs)
        if len(self.elements) != n:
            raise ValueError("Non matching number of tree leaves and permutations length.")
        self._tag_()
        
    def _tag_(self):        
        ## Tag leaves
        for e, n in zip(self.elements, TreeIterator(self.tree, Tree.is_leaf)):
            n.permutation_index = e
        ## Tag Nodes
        TreePermutation._tag_nodes_(self.tree)

    @staticmethod
    def _tag_nodes_(node):
        """
        Tag each node with the leaf having the smallest index.
        """
        if node.is_leaf():
            return
        for n in node.children:
            TreePermutation._tag_nodes_(n)
            
        node.permutation_index = min([ n.permutation_index for n in node.children ])
        subtrees = []
        for n in node.children:
            if not any([ n.is_equal(t) for t in subtrees ]):
                subtrees.append(n)
        node.grouped_children = [ [ i for (i,c) in zip(range(len(node.children)), node.children) if c.is_equal(t) ] for t in subtrees ]

    def shuffle(self):        
        """
        Return a new random permutation based on this permutation.
        """
        shuffle(self.elements)
        self._tag_()
        return self

    def _update_elements_(self):
        self.elements = [ n.permutation_index for n in self.tree if n.is_leaf() ]
        
    def canonical(self):
        """
        Sort permutation by shifting tree nodes based on the smallest leaf.
        Modifies this object in place.
        """        
        ## Sort every node based on their permutation index.
        nodes = [ n for n in self.tree if hasattr(n, 'grouped_children') ]
        for n in nodes:
            for g in n.grouped_children:
                srted = sorted([(n.children[i].permutation_index,i) for i in g])
                n.swap([ s[1] for s in srted ])
        self._update_elements_()
        return self

    def is_canonical(self) -> bool:
        """
        Return True if the permutation is already in a canonical form.
        """
        for n in self.tree:
            if not hasattr(n, 'grouped_children'):
                continue
            # Check that each individual group is ordered
            for group in n.grouped_children:
                group = [ n.children[i] for i in group ]
                index = [ c.permutation_index for c in n.children if c in group ]
                for i, j in zip(index[1:], index):
                    if i < j:
                        return False
        return True

    class Coords(list):
        def __hash__(self):
            if len(self) == 0:
                return -1
            return sum([ self[i] * (len(self) ** i) for i in range(len(self)) ])
            
    def print(self, display_tree=True):
        """
        +
        |
        +--------+
        |        |
        +---+    +---+
        |   |    |   |
        +   +    +   +
        0   1    2   3
        """
        if display_tree:
            leaves = [ n for n in self.tree if n.is_leaf() ]
            sizes = [ len(str(l.permutation_index)) for l in leaves ]
            lengths = {}
            for i, l in zip(range(len(sizes)), leaves):
                off = i*2 + sum(sizes[:i])
                coords = TreePermutation.Coords(l.coords())
                lengths[coords] = off
                while len(coords) > 0 and coords[-1] == 0:
                    coords = TreePermutation.Coords(coords[:-1])
                    lengths[coords] = off
                if len(coords) == 0:
                    lengths[coords] = off

            depth = self.tree.max_depth()
            for i in range(depth+1):
                i_line = ''
                s_line = ''
                for n in self.tree:
                    if n.get_depth() != i:
                        continue
                    coords = TreePermutation.Coords(n.coords())
                    offset = lengths[coords]
                    if len(coords) > 0 and coords[-1] == 0:
                        i_line += ' ' * (offset - len(i_line))
                    else:
                        i_line += '-' * (offset - len(i_line))
                    s_line += ' ' * (offset - len(s_line))
                    i_line += str(n.permutation_index)
                    s_line += '|' + ' ' * (len(str(n.permutation_index))-1)
                print(i_line)
                if i < depth:
                    print(s_line)
        print('  '.join([str(i) for i in self.elements]))
        
    def shuffle_nodes(self):
        """
        Shuffle this permutation by shuffling tree nodes children.
        Only children with the same amount of leaves can be shuffled
        together.
        Modifies this object in place.
        """
        for node in TreeIterator(self.tree, lambda n: not n.is_leaf()):
            for g in node.grouped_children:
                shuffle(g)
                node.swap(g)
        self._update_elements_()
        return self

__all__ = [ 'Permutation', 'TreePermutation' ]

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
            self.assertNotEqual(copy.shuffle(), permutation)
        
    def test_id(self):
        for id, permutation in zip(self.ids, self.permutations):
            # assert permutation built by id yields the same id.
            self.assertEqual(id, permutation.id())
            # assert that shuffled permutation id will build the same
            # permutation 
            shuffled = permutation.copy().shuffle()
            permutation = Permutation(len(permutation), shuffled.id())
            self.assertEqual(shuffled, permutation)

    def test_add(self):
        for permutation in self.permutations:
            other = Permutation(len(permutation), randint(0, sys.maxsize))
            self.assertEqual((other + permutation).id(),
                             (permutation.id() + other.id()) % permutation.max_id)

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
        cls.permutations = [ TreePermutation(t).shuffle() for t in trees ]
        
    def test_canonical(self):
        for permutation in self.permutations:
            canonical = permutation.canonical()
            self.assertTrue(canonical.is_canonical())
            equivalent = permutation.copy().shuffle_nodes()
            self.assertEqual(equivalent.canonical(), canonical)

if __name__ == '__main__':
    unittest.main()
