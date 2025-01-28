# pymsh

<p>
   <img alt="PyPI" src="https://img.shields.io/pypi/v/pymsh?color=blue">
   <img alt="PyPI - Python Version" src="https://img.shields.io/pypi/pyversions/pymsh">
   <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/pymsh">
   <img alt="PyPI - License" src="https://img.shields.io/pypi/l/pymsh?label=license">
   <img alt="Test Status" src="https://github.com/cgshep/pymsh/actions/workflows/python-package.yml/badge.svg">
</p>

**pymsh** is a Python library that provides **multiset hash (MSH)** functions. These functions let you hash collections of items _without_ worrying about the order of those items.

## What is a Multiset Hash?

A _multiset_ is like a set, except it can contain multiple instances of the same item. For example:
- A set might be `[apple, banana, cherry]` (with no duplicates).
- A multiset could be `[apple, apple, apple, banana, banana, cherry]` (duplicates matter).

Multiset hashing (MSH) produces a hash value that reflects both the _types_ of items you have and the _quantities_ of each item, but _not_ their order. If we hash the following using an MSH scheme, then the same hash values will be produced: `hash(apple, banana, banana, apple, apple, cherry) == hash(apple, apple, apple, banana, banana, cherry)` 

We can see that the order does not matter as long as the elements and their quantities are the same.

### Why Is This Useful?

If you have a collection of elements where order does not matter (e.g., tags on a file, items in a shopping cart), a normal hash function, such as SHA256 or MD5, will give different results depending on how you list the items. A multiset hash ensures the same final hash regardless of item ordering.

Furthermore, some MSHs in this library can be updated one item at a time. This is especially handy if you handle large or streaming data and want to maintain a running hash without reprocessing everything.

## Installation

```bash
pip install pymsh
```

## Basic Usage

For most general use cases, we recommend using the **additive multiset hash** (accessible via the shortcut class `Hasher`).

1. **Prepare a multiset**: You can use our helper `list_to_multiset` if you have a Python list containing repeated elements.
2. **Hash it**: Pass the resulting dictionary (`element -> count`) into a hasher.

*Note: pymsh expects your inputs to be passed as bytes.*

Example:
```python
from pymsh import list_to_multiset, Hasher

# Suppose you have this list with repeated elements
fruit_list = [b"apple", b"apple", b"banana", b"cherry", b"banana", b"apple"]

# 1) Convert the list to a multiset:
multiset = list_to_multiset(fruit_list)
# => {b"apple": 3, b"banana": 2, b"cherry": 1}

# 2) Hash your multiset (Hasher is an alias for MSetAddHash)
msh = Hasher().hash(multiset)
print("Multiset hash:", msh)
```

That’s it! You’ll get a tuple representing the multiset, independent of how you ordered "apple, banana, cherry."

## Advanced Usage

`pymsh` implements multiple MSH constructions, each with its own tradeoffs in security, performance, and whether it requires a secret key. Below is a quick overview; skip to **Incremental vs. One-shot Hashing** if you don’t need these details right now.


<details>
<summary><strong>MSetXORHash</strong> (Keyed, Set-collision Resistant)</summary>

- **What it does**: A keyed hash using XOR operations internally.
- **Best for**: Cases where you only need to detect changes in the set of items (ignores the exact count of each item, though).
- **Supports incremental hashing?**: Yes.
- **Uses a secret key**: Yes.
- It is **NOT** multiset collision-resistant; if some of your elements repeat, then the same hash values may be produced for different orderings.
</details>


<details>
<summary><strong>MSetAddHash</strong> (Keyed, Multiset-collision Resistant)</summary>

- **What it does**: Uses an additive approach under a secret key to ensure that different multisets produce distinct hashes.
- **Best for**: Most general-purpose scenarios. This is the same as the default `Hasher` class.
- **Supports incremental hashing?**: Yes.
- **Uses a secret key**: Yes.
</details>

<details>
<summary><strong>MSetMuHash</strong> (Keyless, Multiset-collision Resistant)</summary>

- **What it does**: Uses multiplication in a finite field (large prime modulus).
- **Best for**: Keyless scenarios with a short output size. Good when you want collision resistance without managing keys.
- **Supports incremental hashing?**: No.
- **Uses a secret key**: No.
</details>

<details>
<summary><strong>MSetVAddHash</strong> (Keyless, Multiset-collision Resistant)</summary>

- **What it does**: Uses vector addition space.
- **Best for**: Keyless scenarios with incremental updates; yields a larger hash compared to MuHash, but often simpler to handle incrementally.
- **Supports incremental hashing?**: Yes.
- **Requires a Key**: No.
</details>

### Examples

```python
import secrets
from pymsh import (
    MSetXORHash,
    MSetAddHash,
    MSetMuHash,
    MSetVAddHash
)

# Sample secret key for keyed hashes
key = secrets.token_bytes(32)

# A sample multiset: item -> count
multiset = {
    b"apple": 3,
    b"banana": 2,
    b"cherry": 1
}

# 1) XOR Hash (Keyed, set-collision resistant)
xor_hasher = MSetXORHash(key)
xor_result = xor_hasher.hash(multiset)
print("XOR Hash (one-shot):", xor_result)

# 2) Additive Hash (Keyed, multiset-collision resistant)
add_hasher = MSetAddHash(key)
one_shot = add_hasher.hash(multiset)
print("Additive Hash (one-shot):", one_shot)

# Incremental usage of Additive Hash
add_hasher.update(b"apple", 3)
add_hasher.update(b"banana", 2)
add_hasher.update(b"cherry", 1)
incremental_hash = add_hasher.digest()
print("Additive Hash (incremental):", incremental_hash)
assert one_shot == incremental_hash  # They should match

# 3) MuHash (Keyless)
mu_hasher = MSetMuHash()
print("MuHash:", mu_hasher.hash(multiset))

# 4) Vector Add Hash (Keyless)
vadd_hasher = MSetVAddHash()
print("VAdd Hash:", vadd_hasher.hash(multiset))
```

---

## Incremental vs. One-shot Hashing

**One‐shot**: Pass a full dictionary (e.g., `{item: count}`) at once using `.hash(multiset)`.

**Incremental**: Create an instance, then call `.update(item, count)` for each new element as needed, and finally call `.digest()` to get the final hash.

## Which Should I Pick?

For most **general-purpose** tasks, use **MSetAddHash** (the default `Hasher`).

If you prefer **keyless** usage or want a smaller output size, consider **MSetMuHash**. However, if you need **incremental** and **keyless**, try **MSetVAddHash**. Here's a comparison table:

| Hash Type       | Security          | Key Required | Incremental | Notes                        |
|-----------------|-------------------|--------------|-------------|------------------------------|
| `MSetXORHash`   | Set-collision resistance    | Yes          | Yes         | Fast set verification        |
| `MSetAddHash`   | Multiset-collision resistance | Yes          | Yes         | General purpose              |
| `MSetMuHash`    | Multiset-collision| No           | No          | Keyless; short outputs       |
| `MSetVAddHash`  | Multiset-collision| No           | Yes         | Efficient, but longer hashes |


## References

1. D. Clarke, S. Devadas, M. van Dijk, B. Gassend, and G.E. Suh. [“Incremental Multiset Hash Functions and Their Application to Memory Integrity Checking,”](https://www.iacr.org/cryptodb/data/paper.php?pubkey=151) ASIACRYPT 2003.

## Note
This project has not been audited or verified; do not rely on this library for serious production systems.

## Contribute

Feel free to open an issue or pull request if you have questions or suggestions!
