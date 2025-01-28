import pytest
import secrets

from pymsh import MSetXORHash


def test_same_multiset_same_hash():
    """Two identical multisets should produce the same final digest."""
    key = secrets.token_bytes(32)
    fixed_nonce = b'\x00'*16  # or some test value
    hasher1 = MSetXORHash(key, m=256, nonce=fixed_nonce)
    hasher2 = MSetXORHash(key, m=256, nonce=fixed_nonce)

    multiset = {
        b'apple': 1,
        b'banana': 3,
        b'carrot': 2,
    }

    for elem, cnt in multiset.items():
        hasher1.update(elem, cnt)
        hasher2.update(elem, cnt)

    assert hasher1.digest() == hasher2.digest(), \
        "Digests differ for same multiset."


def test_different_multiset_differs():
    """
    Changing at least one element or multiplicity should
    change the hash with high probability.
    """
    key = secrets.token_bytes(32)
    fixed_nonce = b'\x00'*16  # or some test value
    hasher_original = MSetXORHash(key, m=256, nonce=fixed_nonce)
    hasher_modified = MSetXORHash(key, m=256, nonce=fixed_nonce)

    multiset_original = {
        b'apple': 1,
        b'banana': 3,
        b'carrot': 2,
    }
    multiset_modified = {
        b'apple': 1,
        b'banana': 3,
        b'carrot': 3,  # changed multiplicity
    }

    for elem, cnt in multiset_original.items():
        hasher_original.update(elem, cnt)
    for elem, cnt in multiset_modified.items():
        hasher_modified.update(elem, cnt)

    digest_original = hasher_original.digest()
    digest_modified = hasher_modified.digest()

    # They might accidentally collide, but it's unlikely for a 256-bit hash.
    # We just check that they're not trivially equal.
    assert digest_original != digest_modified, \
        "Expected different digests for different multisets."


def test_negative_multiplicity_raises():
    """update() with negative multiplicity should raise ValueError."""
    key = secrets.token_bytes(32)
    hasher = MSetXORHash(key)
    with pytest.raises(ValueError):
        hasher.update(b'something', -2)


def test_empty_multiset():
    """
    Hashing an empty multiset is just H_K(0, r) in the XOR part,
    0 for the count, plus r.
    """
    key = secrets.token_bytes(32)
    hasher = MSetXORHash(key)
    digest = hasher.digest()

    # The digest should have 3 parts
    assert len(digest) == 3, "digest() should return (xor_val, count, nonce)."

    xor_val, total_count, nonce = digest
    # total_count should be 0 for an empty multiset
    assert total_count == 0
    # xor_val = H_K(0, r) for an empty set
    # We cannot easily check it directly, but at least verify it's an integer
    assert isinstance(xor_val, int)
    # nonce is 16 random bytes
    assert isinstance(nonce, bytes) and len(nonce) == 16


def test_sum_of_multiplicities():
    """
    Ensure that the total_count is indeed the sum of
    all multiplicities mod 2^m."""
    key = secrets.token_bytes(32)
    m = 10  # small-ish so we can check wrap-around if needed
    hasher = MSetXORHash(key, m=m)
    # 2^m = 1024
    # We'll add enough elements to exceed 1024 and verify wrap-around
    multiset = {
        b'elem1': 500,
        b'elem2': 300,
        b'elem3': 300,
    }
    for elem, count in multiset.items():
        hasher.update(elem, count)

    xor_val, total_count, nonce = hasher.digest()
    expected = (500 + 300 + 300) % (1 << m)  # % 1024
    assert total_count == expected, \
        "total_count does not match sum of multiplicities mod 2^m"


def test_hash_method():
    """
    Check that hasher.hash(multiset) produces the same
    result as doing incremental updates.
    """
    fixed_nonce = b'\x00'*16
    key = secrets.token_bytes(32)
    hasher = MSetXORHash(key, m=256, nonce=fixed_nonce)
    multiset = {
        b'a': 1,
        b'b': 2,
        b'c': 5
    }

    digest_via_hash = hasher.hash(multiset)
    hasher2 = MSetXORHash(key, m=256, nonce=fixed_nonce)
    for elem, mult in multiset.items():
        hasher2.update(elem, mult)

    digest_via_manual = hasher2.digest()

    assert digest_via_hash == digest_via_manual, \
        "hash() method differs from manual incremental update."
