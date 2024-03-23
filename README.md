# pymsh

<p>
   <img alt="PyPI" src="https://img.shields.io/pypi/v/voyager-cpu?color=blue">
   <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/voyager-cpu">
   <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/voyager-cpu">
   <img alt="PyPI - License" src="https://img.shields.io/pypi/l/voyager-cpu?label=license">
</p>

pymsh is an MIT-licensed implementation of the incremental multi-set hashing (MSH) scheme proposed by Clarke et al. [1] (ASIACRYPT '03). Specifically, it supports the XOR construction for fast updates; BLAKE2B is used as the underlying hash function.

## Usage

Simple: initialise the `MSH()` class and call `hash(...)` for hashing multisets directly, or `update(...)` for incremental updates.

Examples:
```python





## References
1. Clarke, D., Devadas, S., van Dijk, M., Gassend, B., Suh, G.E. (2003). *"Incremental Multiset Hash Functions and Their Application to Memory Integrity Checking."* In: Advances in Cryptology - ASIACRYPT. Lecture Notes in Computer Science, vol 2894. Springer, Berlin, Heidelberg. [https://doi.org/10.1007/978-3-540-40061-5_12](https://doi.org/10.1007/978-3-540-40061-5_12)