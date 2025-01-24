# pymsh

<p>
   <img alt="PyPI" src="https://img.shields.io/pypi/v/pymsh?color=blue">
   <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/pymsh">
   <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/pymsh">
   <img alt="PyPI - License" src="https://img.shields.io/pypi/l/pymsh?label=license">
   <img alt="Test Status" src="https://github.com/cgshep/pymsh/actions/workflows/python-package.yml/badge.svg">
</p>

**pymsh** is a Python implementation of **incremental multiset hash functions** (MSHs) from Clarke et al. [1]. It provides multiple methods with different security and performance tradeoffs:

- **MSetXORHash**: XOR-based (set-collision resistant),
- **MSetAddHash**: Additive-based (multiset-collision resistant) with incremental updates,
- **MSetMuHash**: Multiplicative-based (multiset-collision resistant) in a finite field, keyless,
- **MSetVAddHash**: Vector-addition–based (multiset-collision resistant), can be incremental.

An **MSH** is a hash that is invariant under permutation of the input elements. That is, $H(\{a,b,c\}) = H(\{c,b,a\})$.

This property is useful for hashing data structures where order does not matter. Each of these implementations has a slightly different internal design to accommodate various security or performance needs.


## Installation

```bash
pip install pymsh
```

## Dependencies

sympy (for prime generation)

## Basic Usage

MSetAddHash is great for general-purpose usage. Let's assume we have a list with some repeated elements, such as `["apple", "apple", "banana", "cherry", "banana", "apple"]`

We can use the helper function `list_to_multiset` to produce a multiset (pymsh expects byte representations of strings):
```python
from pymsh import list_to_multiset, Hasher

lst = [b"apple", b"apple", b"banana", b"cherry", b"banana", b"apple"]
multiset = list_to_multiset(lst)
```
This gives us:
```python
{b"apple": 3, b"banana": 2, b"cherry": 1}
```
We can then use our general `Hasher` class, a synonym for the general-purpose `MSetAddHash` class, as follows:
```python
msh = Hasher().hash(multiset)
```

It's that easy! 


## Advanced Usage

You can use other constructions using the below examples. You can either do one‐shot hashing of a Python dict (representing the multiset), or use incremental updates where supported.

```python
import secrets

from pymsh import MSetXORHash, MSetAddHash, MSetMuHash, MSetVAddHash

# Example secret key for keyed hashes (XOR and Add variants).
key = secrets.token_bytes(32)

# A sample multiset with elements as bytes and integer multiplicities
multiset = {
    b"apple":  3,
    b"banana": 2,
    b"cherry": 1
}

#
# 1) XOR Hash (set-collision resistant, keyed, incremental)
#
xor_hasher = MSetXORHash(key)
print("XOR Hash (one-shot):", xor_hasher.hash(multiset))

#
# 2) Additive Hash (multiset-collision resistant, keyed, incremental)
#
add_hasher = MSetAddHash(key)
one_shot = add_hasher.hash(multiset)
print("Additive Hash (one-shot):", one_shot)

# You can also do incremental updates:
add_hasher.update(b"apple", 3)
add_hasher.update(b"banana", 2)
add_hasher.update(b"cherry", 1)
incremental_hash = add_hasher.digest()
print("Additive Hash (incremental):", incremental_hash)

# Confirm that the one-shot and incremental values are the same
assert one_shot == incremental_hash

#
# 3) Multiplicative Hash in GF(q) (multiset-collision resistant, keyless)
#
mu_hasher = MSetMuHash()  # typically you set a large prime q
print("MuHash:", mu_hasher.hash(multiset))

#
# 4) Vector Add Hash (keyless, can be incremental, typically larger output)
#
vadd_hasher = MSetVAddHash()
print("VAdd Hash (one-shot):", vadd_hasher.hash(multiset))
```

## Incremental vs. One-shot

- *Incremental:* You create an instance, call `.update(element, multiplicity)` repeatedly, then `.digest()` to obtain the final hash.
- *One‐shot:* You simply call `.hash(multiset)` once with a dictionary of element -> multiplicity.

MSetXORHash and MSetAddHash are both keyed and incremental in this repository, while MSetMuHash is unkeyed and typically one-shot (though it could be adapted), and MSetVAddHash is keyless and incremental.

## Comparing Methods

| Hash Type       | Security          | Key Required | Incremental | Notes                        |
|-----------------|-------------------|--------------|-------------|------------------------------|
| `MSetXORHash`   | Set-collision resistance    | Yes          | Yes         | Fast set verification        |
| `MSetAddHash`   | Multiset-collision resistance | Yes          | Yes         | General purpose              |
| `MSetMuHash`    | Multiset-collision| No           | No          | Keyless; short outputs       |
| `MSetVAddHash`  | Multiset-collision| No           | Yes         | Efficient, but longer hashes |

## References

1. D. Clarke, S. Devadas, M. van Dijk, B. Gassend, and G.E. Suh. ["Incremental Multiset Hash Functions and Their Application to Memory Integrity Checking,"](https://www.iacr.org/cryptodb/data/paper.php?pubkey=151) ASIACRYPT 2003.