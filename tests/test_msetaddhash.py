import secrets
import pytest

from pymsh import MSetAddHash


def test_same_multiset_same_hash():
    """
    Two calls to 'hash()' on the *same* hasher with the *same* multiset
    should yield the same result, because the nonce and key haven't changed.
    """
    key = secrets.token_bytes(32)
    hasher = MSetAddHash(key, m=256)

    multiset = {
        b'cat': 3,
        b'dog': 5
    }
    digest1 = hasher.hash(multiset)
    digest2 = hasher.hash(multiset)

    assert digest1 == digest2, (
        "Expected the same digest for the same hasher, key, and multiset."
    )


def test_different_multiset_different_hash():
    """
    Hashes of two distinct multisets should differ with high probability.
    (They *could* collide, but it's cryptographically unlikely.)
    """
    key = secrets.token_bytes(32)
    hasher = MSetAddHash(key, m=256)

    multiset_a = {b'apple': 1, b'banana': 2}
    multiset_b = {b'apple': 2, b'banana': 1}  # swapped multiplicities

    digest_a = hasher.hash(multiset_a)
    digest_b = hasher.hash(multiset_b)
    assert digest_a != digest_b, (
        "Expected different digests for multisets, but got a collision."
    )


def test_negative_multiplicity():
    """Negative multiplicities should raise ValueError."""
    key = secrets.token_bytes(32)
    hasher = MSetAddHash(key, m=256)
    with pytest.raises(ValueError):
        hasher.hash({b'bad': -1})  # Should raise an error


def test_empty_multiset():
    """
    Hashing an empty multiset should just be H(0, nonce) mod 2^m,
    plus the nonce.
    """
    key = secrets.token_bytes(32)
    hasher = MSetAddHash(key, m=256)
    digest, nonce = hasher.hash({})

    # digest should be an integer, nonce is 16 random bytes
    assert isinstance(digest, int), "Digest must be an integer."
    assert isinstance(nonce, bytes) and len(nonce) == 16, \
        "Nonce must be 16 bytes."
    # We can't easily predict what H(0, nonce) will be,
    # but at least we know there's no error.


def test_small_modulus():
    """
    Use a small m (e.g. 8 bits) so we can check that big
    multiplicities wrap around mod 2^m.
    """
    key = secrets.token_bytes(32)
    m = 8
    hasher = MSetAddHash(key, m)
    # 2^8 = 256, let's exceed that
    multiset = {
        b'x': 300,  # 300 % 256 = 44
    }
    digest, nonce = hasher.hash(multiset)
    # Just check it's an integer in [0, 255].
    assert 0 <= digest < 256, f"Digest={digest} should be in [0,255] for m=8."


def test_consistency_between_instances():
    """
    If we want two distinct MSetAddHash objects (with the *same key & nonce*)
    to produce the same hash for the same multiset, we must ensure they
    share the exact same nonce. Demonstrate by copying the nonce from hasher1.
    """
    key = secrets.token_bytes(32)
    hasher1 = MSetAddHash(key, m=256)
    multiset = {b'alpha': 10, b'beta': 20}

    digest1 = hasher1.hash(multiset)

    # Create hasher2 with the same key, but it randomizes nonce by default:
    hasher2 = MSetAddHash(key, m=256)
    # Overwrite hasher2.nonce to match hasher1's.
    hasher2.nonce = hasher1.nonce

    digest2 = hasher2.hash(multiset)
    assert digest1 == digest2, (
        "Two MSetAddHash objects with identical key+nonce not the same!"
    )


def test_incremental_vs_one_shot():
    key = secrets.token_bytes(32)
    hasher = MSetAddHash(key)

    # Build the same final multiset incrementally
    hasher.update(b'alpha', 2)
    hasher.update(b'beta', 1)
    hasher.update(b'alpha', 3)
    hasher.update(b'beta', 1)
    hasher.update(b'beta', 19)
    digest_inc = hasher.digest()

    # Compare with one-shot
    reference_multiset = {b'alpha': 5, b'beta': 21}
    digest_one_shot = hasher.hash(reference_multiset)
    assert digest_inc == digest_one_shot, "Incremental must match one-shot"
