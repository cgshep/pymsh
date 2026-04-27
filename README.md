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
- `[apple, banana, cherry]` is a set (no duplicates).
- `[apple, apple, apple, banana, banana, cherry]` is a multiset (same elements, but duplicates matter).

Multiset hashing (MSH) produces a hash value that reflects both the _types_ of items you have and the _quantities_ of each item, but _not_ their order. If we hash the following using an MSH scheme, then the same hash values will be produced: `hash(apple, banana, banana, apple, apple, cherry)` will equal `hash(apple, apple, apple, banana, banana, cherry)` 

We can see that the _order does not matter_ as long as the elements and their _quantities_ are the same.

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
hasher = Hasher()
digest, nonce = hasher.hash(multiset)
print("Multiset hash:", digest.hex(), "nonce:", nonce.hex())
```

That's it! You get a `(digest, nonce)` tuple representing the multiset, independent of how you ordered "apple, banana, cherry." To reproduce the hash on another device you need the **key** (`hasher.key`) and the **nonce** (the second tuple element). Both must be passed back to `MSetAddHash(key=..., nonce=...)` to obtain the same digest.

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

- **What it does**: Uses multiplication in a finite field with a large prime modulus. Slow.
- **Best for**: Keyless scenarios. Good when you want collision resistance without managing keys.
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

If you prefer **keyless** usage without the **incremental** feature, then consider **MSetMuHash**.

However, if you need **incremental** and **keyless**, try **MSetVAddHash**. Here's a comparison table:

| Hash Type       | Security          | Key Required | Incremental | Notes                        |
|-----------------|-------------------|--------------|-------------|------------------------------|
| `MSetXORHash`   | Set-collision resistance    | Yes          | Yes         | Fast set verification        |
| `MSetAddHash`   | Multiset-collision resistance | Yes          | Yes         | General purpose              |
| `MSetMuHash`    | Multiset-collision| No           | No          | Keyless; not efficient       |
| `MSetVAddHash`  | Multiset-collision| No           | Yes         | Efficient, but longer hashes |


## When Would I Use This?

Anywhere you have a *collection of things where order doesn't matter* and you
want a single small fingerprint of it. A normal hash like SHA-256 changes the
moment you reorder the input; a multiset hash doesn't.

### 1. Verify two SQL queries return the same rows

A `SELECT` without an `ORDER BY` makes no promise about the row order, and
result sets can contain duplicates — so a Python `set()` would silently lose
information. Hash the multiset of rows on each side and compare two small
fingerprints instead.

```python
import json
from pymsh import MSetMuHash, list_to_multiset

result_a = [(1, "alice"), (2, "bob"), (1, "alice"), (3, "carol")]
result_b = [(3, "carol"), (1, "alice"), (2, "bob"), (1, "alice")]   # same rows, reshuffled

def fingerprint(rows):
    serialised = [json.dumps(row).encode() for row in rows]
    return MSetMuHash().hash(list_to_multiset(serialised))

assert fingerprint(result_a) == fingerprint(result_b)
```

Bread-and-butter use cases: checking that a refactored query returns the
same rows as the original, or sanity-checking that two database replicas
agree on a table's contents without scanning row-by-row. Drop one of the
duplicate `(1, "alice")` rows and the fingerprint changes — multiplicities
are preserved, unlike with a plain `set()`.

### 2. "Do these two documents use the same words?"

A bag-of-words fingerprint. Two pieces of text that contain the same words
at the same frequencies — even if the words are scrambled — get the same
fingerprint.

```python
from pymsh import MSetMuHash, list_to_multiset

doc_a = "the cat sat on the mat".split()
doc_b = "mat the on sat the cat".split()         # same words, scrambled

h = MSetMuHash()
fp_a = h.hash(list_to_multiset([w.encode() for w in doc_a]))
fp_b = h.hash(list_to_multiset([w.encode() for w in doc_b]))
assert fp_a == fp_b
```

Useful for spotting duplicate or near-duplicate text without storing the
original words, and for cheap plagiarism / dedup pre-filters.

### 3. Keep a running fingerprint as data streams in

When you don't have the whole collection up front — you're consuming items
one at a time — you can keep a running fingerprint and ask for it whenever
you need it. The result is the same as if you'd had the whole collection
at once.

```python
from pymsh import MSetVAddHash

running = MSetVAddHash()
for word in "the cat sat on the mat".split():
    running.update(word.encode(), 1)             # one item at a time

print(running.digest().hex())                    # final fingerprint
```

This is what makes multiset hashes interesting for things like inventory
counters, log fingerprints, or any "running tally" where you don't want
to re-hash everything from scratch each time something changes.

## References

1. D. Clarke, S. Devadas, M. van Dijk, B. Gassend, and G.E. Suh. [“Incremental Multiset Hash Functions and Their Application to Memory Integrity Checking,”](https://www.iacr.org/cryptodb/data/paper.php?pubkey=151) ASIACRYPT 2003.

## Development

Clone the repo and install the test extras:

```bash
pip install -e ".[test]"
pytest                  # run the test suite
mypy pymsh.py           # type-check
```

A wheel and sdist can be built with `python -m build` (requires the
[`build`](https://pypi.org/project/build/) package).

## Contribute

Feel free to open an issue or pull request if you have questions or suggestions!
