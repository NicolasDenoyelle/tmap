# TMAP

Python module to compute permutations and map them on trees

## Install
```
pip install .
```

## Test
```
python -m unittest tmap/permutation.py tmap/tree.py
```

## Examples:

### Simple Permutations

* Create a permutation of n elements:
```
from tmap import Permutation

p = Permutation(6)
print(p) # '0:1:2:3:4:5'
```

* shuffle the permutation
```
s = p.shuffled()
print(s) # 5:3:4:1:0:2
```

* permutation integer identifier enables arithmetic on permutations:
```
Permutation(len(s), s.id()) == s
```

* permutation is iterable and deref:
```
print(':'.join([ str(i) for i in s])) # 5:3:4:1:0:2
print(s[0]) # 5
```

### Trees

* Build a Tleaf Tree:
```
from tmap import Tleaf
tree = Tleaf(arities=[2,3])
print(tree)
```

```
    +------[0, 0]
    |         
    +------[0, 1]
    |         
    +------[0, 2]
+---[0]
|      
|   +------[1, 0]
|   |         
|   +------[1, 1]
|   |         
|   +------[1, 2]
+---[1]
```

* Trees are iterable:
```
for node in tree:
		print(node.coords)
```
```
[0, 0]
[0, 1]
[0, 2]
[0]
[1, 0]
[1, 1]
[1, 2]
[1]
[]
```

### Map a Tree on a Permutation:
```
from tmap import TreePermutation
p = TreePermutation(tree, s.id())
print(p) #5:3:4:1:0:2
```

* A canonical representation of this Permutation mapped on this Tree,
is a permutation of the Tree nodes such that tree levels are sorted based
on the minimum leaf index.

```
can = p.canonical()
print(can) # 0:1:2:3:4:5
# It happens here that the canonical representation
of the shuffled permutation was the permutation it self.

p = TreePermutation(tree, Permutation([0,1,3,2,4,5]).id())
print(p.canonical()) # 0:1:3:2:4:5
```

* A canonical permutation is a unique permutation of a subgroup.
Other permutations of the same subgroup can be randomly generated
by shuffling tree nodes.

```
equi = p.shuffled_equivalent()
print(equi) # 2:5:4:3:0:1
print(equi.canonical() == p) # True
```

### Load a Machine Topology
* This part will only be available if hwloc is installed on the system.

```
from tmap import Topology
this_system_topology = Topology()
print(this_system_topology)
topology = Topology(input_topology='node:2 l3:1 pu:4')
print(topology)
```
```
    +------PU:0
    |         
    +------PU:1
    |         
    +------PU:2
    |         
    +------PU:3
+---L3Cache:0
|      
|   +------PU:4
|   |         
|   +------PU:5
|   |         
|   +------PU:6
|   |         
|   +------PU:7
+---L3Cache:1
```

### Map a Permutation with this Machine Topology

```
p = TreePermutation(topology)
p
```
```
[0, 1, 2, 3, 4, 5, 6, 7]
```
### Generate a Random Permutation by Shuffling Topology Tree Nodes

```
p.shuffled_equivalent()
[7, 5, 6, 4, 2, 1, 3, 0]
```
L3s have been swapped and PUs inside L3s have been shuffled.

### Enumerate Canonical Permutations of the Topology Tree:

```
from tmap import CanonicalPermutationIterator
for permutation in CanonicalPermutationIterator(p):
		print(permutation)		
```
```
0:1:2:3:4:5:6:7
0:1:2:4:3:5:6:7
0:1:3:4:2:5:6:7
0:2:3:4:1:5:6:7
...
```
