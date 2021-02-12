from functools import reduce

def concat(lists):
    """
    Take nested lists and make it a single level list.
    """
    return reduce(lambda x, y: x+y, lists, [])

def argmin(l):
    """
    Get index of min element in list
    """
    return min(zip(l, range(len(l))))[1]

def which(l, cond):
    """
    Return index of next element in list l satisfying condition cond.
    """
    return next((y[0] for y in zip(range(len(l)), l) if cond(y[1])), None)

def order(l, key=lambda x: x):
    """
    Get an index that would reorder list l.
    """
    return [x[1] for x in sorted(zip(l, range(len(l))), key=lambda x: key(x[0]))]

def isindex(l):
    """
    Return True is l contains all integers of range(len(l)) else false.
    """
    return next((False for i in range(len(l)) if i not in l), True)

def factorial(n):
    r = 1
    while n > 1:
        r = r * n
        n = n - 1
    return r
    
__all__ = [ 'unlist', 'argmin', 'which', 'order', 'isindex', 'factorial' ]
