"""Cross-cutting properties shared by every multiset hash in pymsh.

These are the fundamental guarantees a multiset hash must offer:
empty equals empty, identical multisets hash identically, distinct
multisets hash differently with overwhelming probability, and
order is irrelevant to the result.
"""
import secrets

import pytest

from pymsh import (
    MSetAddHash,
    MSetMuHash,
    MSetVAddHash,
    MSetXORHash,
    list_to_multiset,
)


def _stable_xor():
    return MSetXORHash(key=b"\x00" * 32, m=256, nonce=b"\x00" * 16)


def _stable_add():
    return MSetAddHash(key=b"\x00" * 32, m=256, nonce=b"\x00" * 16)


@pytest.fixture(
    params=[
        pytest.param(_stable_xor, id="MSetXORHash"),
        pytest.param(_stable_add, id="MSetAddHash"),
        pytest.param(MSetMuHash, id="MSetMuHash"),
        pytest.param(MSetVAddHash, id="MSetVAddHash"),
    ]
)
def hasher_factory(request):
    return request.param


def test_same_multiset_same_hash(hasher_factory):
    multiset = {b"apple": 3, b"banana": 2, b"cherry": 1}
    assert hasher_factory().hash(multiset) == hasher_factory().hash(multiset)


def test_empty_equals_empty(hasher_factory):
    assert hasher_factory().hash({}) == hasher_factory().hash({})


def test_empty_differs_from_non_empty(hasher_factory):
    multiset = {b"apple": 3, b"banana": 2, b"cherry": 1}
    assert hasher_factory().hash(multiset) != hasher_factory().hash({})


def test_order_irrelevant(hasher_factory):
    forward = list_to_multiset([b"apple", b"banana", b"cranberry", b"date"])
    reverse = list_to_multiset([b"date", b"cranberry", b"banana", b"apple"])
    assert hasher_factory().hash(forward) == hasher_factory().hash(reverse)


def test_different_counts_different_hash(hasher_factory):
    a = {b"apple": 1, b"banana": 2}
    b = {b"apple": 2, b"banana": 1}
    assert hasher_factory().hash(a) != hasher_factory().hash(b)


def test_list_to_multiset_roundtrip():
    items = [b"apple", b"apple", b"banana", b"cherry", b"banana", b"apple"]
    assert list_to_multiset(items) == {b"apple": 3, b"banana": 2, b"cherry": 1}


def test_keyed_hashes_differ_under_distinct_keys():
    """Independently-keyed instances must not collide for the same input."""
    multiset = {b"apple": 3, b"banana": 2}
    h1 = MSetXORHash(key=secrets.token_bytes(32), m=256)
    h2 = MSetXORHash(key=secrets.token_bytes(32), m=256)
    assert h1.hash(multiset) != h2.hash(multiset)
