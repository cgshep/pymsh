# pymsh

<p>
   <img alt="PyPI" src="https://img.shields.io/pypi/v/pymsh?color=blue">
   <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/pymsh">
   <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/pymsh">
   <img alt="PyPI - License" src="https://img.shields.io/pypi/l/pymsh?label=license">
</p>

pymsh is an MIT-licensed implementation of the incremental multi-set hashing (MSH) scheme based on Clarke et al. [1] (ASIACRYPT '03).

MSH hashes are invariant under the ordering of elements. In other words, $H( \{ a,b,c \} )$ will produce the same value as $H( \{ c,b,a \} )$. This has some interesting space-efficient applications where we don't require different hash values for different orders.

pymsh currently supports XOR-based hashing. This is the most efficient construction, but it's only set-collision resistant. If the input is *not* a set, then collisions can be produced in a trivial manner, e.g. inputting $(a,a)$ will output $H(0)$. 

Ideally, pymsh would implement a comprehensive range of constructions; for example, using addition modulo large integers and finite field arithmetic. This isn't the case today; please feel free to make a pull request.

Note: BLAKE2b is used as the underlying hash function, but you are free to specify your own.

## Usage

Simple: initialise the `MSH()` class and call `hash(...)` for hashing multisets directly, or `update(...)` for incremental updates.

Examples:
```python
from pymsh import pymsh

msh = pymsh.MSH()
m1 = msh.hash([b'apple', b'apple', b'banana'])
print(m1.hex()) # => Returns the multiset hash value of m1
msh.reset()
m2 = msh.hash([b'banana', b'apple', b'apple'])
print(m2.hex()) # => m2 will == m1
```

An example of the update function:
```python
from pymsh import pymsh

msh = pymsh.MSH()
new_lst = [b'apple']
m3 = msh.hash(new_lst)
print(m3.hex())
m3 = msh.update(b'banana')
print(m3.hex())
m3 = msh.update(b'apple')
print(m3.hex()) # => Equivalent to m2 or m1 above
```

## References
1. Clarke, D., Devadas, S., van Dijk, M., Gassend, B., Suh, G.E. (2003). *"Incremental Multiset Hash Functions and Their Application to Memory Integrity Checking."* In: Advances in Cryptology - ASIACRYPT. Lecture Notes in Computer Science, vol 2894. Springer, Berlin, Heidelberg. [https://doi.org/10.1007/978-3-540-40061-5_12](https://doi.org/10.1007/978-3-540-40061-5_12)
