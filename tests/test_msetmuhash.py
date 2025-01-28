import pytest

from pymsh import MSetMuHash


def test_same_multiset_same_hash():
    """
    The same multiset should always hash to the same product mod q.
    """
    hasher = MSetMuHash()

    multiset = {
        b'apple': 2,
        b'banana': 3,
        b'carrot': 1
    }
    h1 = hasher.hash(multiset)
    h2 = hasher.hash(multiset)
    assert h1 == h2, "Same multiset => same hash."


def test_different_multisets_different_hash():
    """
    Two different multisets are very unlikely to collide,
    though it's theoretically possible. We just check they differ in practice.
    """
    hasher = MSetMuHash()

    ms1 = {b'a': 1, b'b': 2}
    ms2 = {b'a': 2, b'b': 1}  # swapped multiplicities

    h1 = hasher.hash(ms1)
    h2 = hasher.hash(ms2)
    assert h1 != h2, "Distinct multisets should produce distinct results."


def test_negative_multiplicity():
    """
    Negative multiplicities must raise an error.
    """
    hasher = MSetMuHash()
    with pytest.raises(ValueError):
        hasher.hash({b'bad': -5})


def test_empty_multiset():
    """
    By definition, the product over an empty set is 1
    (the 'empty product' is conventionally 1 mod q).
    """
    hasher = MSetMuHash()
    res = hasher.hash({})
    assert res == 1, "Empty product should be 1 mod q."


def test_zero_multiplicity():
    """
    Multiplicity 0 means we skip that element. Product should remain unchanged.
    """
    hasher = MSetMuHash()

    # This is effectively the same as {b'x': 2} because b'y' has count 0
    ms = {b'x': 2, b'y': 0}
    res = hasher.hash(ms)

    # Compare with a set that doesn't even have y
    ms_no_y = {b'x': 2}
    res_no_y = hasher.hash(ms_no_y)

    assert res == res_no_y, "Multiplicity 0 should not affect the product."


def test_exponentiation_wrap():
    """
    Check that large multiplicities are handled properly mod q-1 in exponents,
    if that is relevant. Actually, we do pow(hval, count, q) in Python
    so it is correct even if count >= q.
    """
    q = 1019
    hasher = MSetMuHash(q)

    # Large multiplicity
    ms = {b'big': 10_000_000}
    # Just ensure it doesn't error and yields something in [1..q-1].
    result = hasher.hash(ms)
    assert 0 <= result < q, "Result must be within GF(q)."
