import pytest

from pymsh import MSetVAddHash


def test_empty_multiset():
    """
    With no updates, digest() should be 0, because the sum is empty.
    """
    # let's pick some small n=1019 for demonstration
    hasher = MSetVAddHash(n=1019)
    assert hasher.digest() == 0, "Empty aggregator => sum=0 mod n."


def test_incremental_vs_one_shot():
    """
    If we incrementally add elements, that should match the one-shot
    .hash() of the final multiset.
    """
    hasher = MSetVAddHash()

    # Build alpha=2, beta=3 incrementally
    hasher.update(b'alpha', 2)
    hasher.update(b'beta', 3)
    inc_digest = hasher.digest()

    # Now do a one-shot with the same final multiset
    ms = {b'alpha': 2, b'beta': 3}
    oneshot_digest = hasher.hash(ms)
    assert inc_digest == oneshot_digest, "Incremental should match one-shot."


def test_remove_elements():
    """
    Demonstrate negative multiplicities for removing elements.
    Final sum should match a one-shot approach with the net counts.
    """
    hasher = MSetVAddHash()

    # alpha=5, beta=3
    hasher.update(b'alpha', 5)
    hasher.update(b'beta', 3)

    # Now remove 2 alpha => alpha total=3
    hasher.update(b'alpha', -2)
    # final aggregator => alpha=3, beta=3
    final_sum = hasher.digest()

    # compare with one-shot
    ref_multiset = {b'alpha': 3, b'beta': 3}
    ref_sum = hasher.hash(ref_multiset)
    assert final_sum == ref_sum, \
        "Removing elements yields the correct final sum."


def test_negative_total_count_error():
    """
    If you remove more elements than you've added, total_count goes negative;
    we raise ValueError per the code.
    """
    hasher = MSetVAddHash()
    hasher.update(b'x', 2)
    with pytest.raises(ValueError):
        # removing 3 x => total_count = -1 => error
        hasher.update(b'x', -3)


def test_different_multisets_different_hash():
    """
    Two distinct multisets are quite likely (though not guaranteed)
    to produce different sums mod n. We just check they differ in practice.
    """
    hasher = MSetVAddHash()

    ms1 = {b'a': 1, b'b': 2}
    ms2 = {b'a': 2, b'b': 1}  # swapped multiplicities

    h1 = hasher.hash(ms1)
    h2 = hasher.hash(ms2)
    assert h1 != h2, \
        "Distinct multisets should yield different sums in practice."


def test_small_modulus():
    """
    Use a tiny modulus so big multiplicities wrap around.
    E.g. n=16 -> sums are mod 16
    """
    hasher = MSetVAddHash(n=16)
    # add big multiplicities
    hasher.update(b'x', 100)
    # final sum must be within 0..15
    result = hasher.digest()
    assert 0 <= result < 16, "Result must be mod 16."


def test_zero_update_no_op():
    """
    update(element, 0) should not change the aggregator at all.
    """
    hasher = MSetVAddHash()
    hasher.update(b'foo', 5)
    sum_before = hasher.digest()

    hasher.update(b'foo', 0)
    sum_after = hasher.digest()
    assert sum_before == sum_after, \
        "Updating with multiplicity=0 must do nothing."
