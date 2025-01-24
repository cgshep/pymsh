# pymsh

<p>
   <img alt="PyPI" src="https://img.shields.io/pypi/v/pymsh?color=blue">
   <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/pymsh">
   <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/pymsh">
   <img alt="PyPI - License" src="https://img.shields.io/pypi/l/pymsh?label=license">
   <img alt="Test Status" src="https://github.com/cgshep/pymsh/actions/workflows/tests.yml/badge.svg">
</p>

**pymsh** is a Python implementation of incremental multiset hash functions (MSHs) from Clarke et al. [1], containing for methods with different security-performance tradeoffs:

- `MSetXORHash`: XOR-based
- `MSetAddHash`: Modular addition
- `MSetMuHash`: Finite field multiplication
- `MSetVAddHash`: Vector addition

MSH hashes are invariant under the ordering of elements. In other words, $H( \{ a,b,c \} )$ will produce the same value as $H( \{ c,b,a \} )$. This has some interesting space-efficient applications where we don't require different hash values for different orders.

## Installation

```bash
pip install pymsh
```

## Dependencies

sympy (for prime generation)

## Basic Usage

```python
from pymsh import MSetXORHash, MSetAddHash, MSetMuHash, MSetVAddHash
import os

key = os.urandom(32)  # For keyed hashes
multiset = {
    b"apple": 3,
    b"banana": 2,
    b"cherry": 1
}

# XOR Hash (Set-collision resistant)
xor_hasher = MSetXORHash(key)
print("XOR Hash:", xor_hasher.hash(multiset))

# Additive Hash (Multiset-collision resistant)
add_hasher = MSetAddHash(key)
print("Additive Hash:", add_hasher.hash(multiset))

# Multiplicative Hash
mu_hasher = MSetMuHash()
print("MuHash:", mu_hasher.hash(multiset))

# Vector Hash
vadd_hasher = MSetVAddHash(n=2**16, l=16)
print("Vector Hash:", vadd_hasher.hash(multiset))
```

## Comparing constructions

| Hash Type       | Security          | Key Required | Incremental | Notes                        |
|-----------------|-------------------|--------------|-------------|------------------------------|
| `MSetXORHash`   | Set-collision     | Yes          | Yes         | Fast set verification        |
| `MSetAddHash`   | Multiset-collision| Yes          | Yes         | General purpose              |
| `MSetMuHash`    | Multiset-collision| No           | No          | Keyless; short outputs       |
| `MSetVAddHash`  | Multiset-collision| No           | Yes         | Efficient, but longer hashes |

## References

1. D. Clarke, S. Devadas, M. van Dijk, B. Gassend, and G.E. Suh. ["Incremental Multiset Hash Functions and Their Application to Memory Integrity Checking,"](https://www.iacr.org/cryptodb/data/paper.php?pubkey=151) ASIACRYPT 2003.