import pytest
import os
import math

from pymsh import MSetXORHash, MSetAddHash, MSetMuHash, MSetVAddHash

@pytest.fixture
def hash_data():
    return {
        "key": os.urandom(32),  # Longer key for testing
        "large_multiset": {os.urandom(16): i for i in range(1, 100)},
        "empty_set": {},
        "test_elements": [b'a', b'b', b'c']
    }


def test_empty_vs_nonempty_collision(hash_data):
    """Empty set should never collide with non-empty sets"""
    xor_hasher = MSetXORHash(hash_data["key"])
    add_hasher = MSetAddHash(hash_data["key"])
    
    empty_hash_xor = xor_hasher.hash(hash_data["empty_set"])
    empty_hash_add = add_hasher.hash(hash_data["empty_set"])
    
    for elem in hash_data["test_elements"]:
        nonempty_hash_xor = xor_hasher.hash({elem: 1})
        nonempty_hash_add = add_hasher.hash({elem: 1})
        
        assert empty_hash_xor != nonempty_hash_xor
        assert empty_hash_add != nonempty_hash_add

# --------------------------
# MSet-XOR-Hash Specific Tests
# --------------------------
def test_xor_multiset_order_independence(hash_data):
    """XOR hash should be order-independent"""
    hasher = MSetXORHash(hash_data["key"])
    multiset1 = {b'a': 1, b'b': 2}
    multiset2 = {b'b': 2, b'a': 1}
    
    assert hasher.hash(multiset1) == hasher.hash(multiset2)

def test_xor_even_odd_cancellation():
    """Even multiplicities should cancel out in XOR"""
    key = os.urandom(32)
    hasher = MSetXORHash(key)
    
    multiset_even = {b'a': 2}
    multiset_odd = {b'a': 3}
    empty_hash = hasher.hash({})
    
    # XORing element with itself cancels out
    assert hasher.hash(multiset_even)[0] == empty_hash[0]
    assert hasher.hash(multiset_odd)[0] != empty_hash[0]


# --------------------------
# MSet-Add-Hash Specific Tests
# --------------------------
@pytest.mark.parametrize("modulus", [2**8, 2**16, 2**32])
def test_add_modulus_overflow(hash_data, modulus):
    """Test modulus wrapping behavior"""
    # Correctly compute m for modulus = 2^k
    k = int(math.log2(modulus))
    hasher = MSetAddHash(hash_data["key"], m=k)
    large_mult = modulus + 1
    
    base_hash = hasher.hash({b'a': 1})[0]
    overflow_hash = hasher.hash({b'a': large_mult})[0]
    
    # (1 + n*modulus) ≡ 1 mod modulus
    assert overflow_hash == base_hash
    

def test_add_incremental_vs_bulk(hash_data):
    """Incremental adds should match bulk computation"""
    hasher = MSetAddHash(hash_data["key"])
    elements = hash_data["test_elements"]
    
    # Bulk computation
    bulk_hash = hasher.hash({elem: 1 for elem in elements})[0]
    
    # Incremental computation
    h0 = hasher.H(0, hasher.nonce)  # Get the initial h0 value
    incremental_hash = h0  # Start with h0
    for elem in elements:
        incremental_hash = (incremental_hash + hasher.H(1, elem)) % (1 << 256)
    
    assert bulk_hash == incremental_hash
    

# --------------------------
# MSet-Mu-Hash Specific Tests
# --------------------------
def test_mu_empty_product_identity():
    """Empty product should be multiplicative identity (1)"""
    hasher = MSetMuHash()
    assert hasher.hash({}) == 1

def test_mu_multiplicative_property(hash_data):
    """Hash(multiset1 u multiset2) = Hash(multiset1) * Hash(multiset2) mod q"""
    hasher = MSetMuHash()
    multiset1 = {b'a': 2, b'b': 3}
    multiset2 = {b'c': 4}
    
    hash1 = hasher.hash(multiset1)
    hash2 = hasher.hash(multiset2)
    combined_hash = hasher.hash({**multiset1, **multiset2})
    
    assert combined_hash == (hash1 * hash2) % hasher.q


# --------------------------
# MSet-VAdd-Hash Specific Tests
# --------------------------
def test_vadd_vector_dimensions():
    """Verify vector length matches specification"""
    for l in [4, 8, 16]:
        hasher = MSetVAddHash(l=l)
        vec = hasher.hash({b'a': 1})
        assert len(vec) == l

def test_vadd_element_uniqueness(hash_data):
    """Different elements should produce different vector components"""
    hasher = MSetVAddHash(n=2**32, l=4)
    vec1 = hasher.H(b'a')
    vec2 = hasher.H(b'b')
    
    assert vec1 != vec2


# --------------------------
# Error Handling Tests
# --------------------------
def test_invalid_element_type():
    """Non-bytes elements should raise TypeError"""
    hasher = MSetXORHash(os.urandom(32))
    with pytest.raises(TypeError):
        hasher.hash({"invalid": 1})  # String key instead of bytes

def test_negative_multiplicity():
    """Negative multiplicities should be rejected"""
    hasher = MSetAddHash(os.urandom(32))
    with pytest.raises(ValueError):
        hasher.hash({b'a': -1})

def test_large_multiplicity_handling():
    """Very large multiplicities should be handled correctly"""
    hasher = MSetMuHash()
    try:
        # 1e18 is a stress test for modular exponentiation
        hasher.hash({b'a': 10**18})
    except Exception as e:
        pytest.fail(f"Unexpected error with large multiplicity: {e}")


def test_large_multiset_performance(hash_data):
    """Test performance with 1,000,000 elements"""
    hasher = MSetVAddHash()
    large_multiset = {os.urandom(16): i for i in range(1000000)}
    
    # Just verify completion, not timing
    result = hasher.hash(large_multiset)
    assert len(result) == hasher.l
