"""
A Python implementation of incremental multiset hash functions for memory integrity checking and cryptographic applications.
"""
import os
import hmac

from hashlib import sha256
from sympy import randprime

class MSetXORHash:
    """
    XOR-based multiset hash function with set-collision resistance;
    supports incremental use cases.
    
    :param key: Secret key (>32 recommended)
    :type key: bytes
    :param m: Bit-length of output hash (default 256)
    :type m: int
    """    
    def __init__(self, key: bytes, m: int = 256):
        """Initialize XOR-based multiset hasher."""
        self.key = key
        self.m = m
        self.nonce = os.urandom(16)

    def H(self, prefix: int, b: bytes) -> int:
        """
        Internal hash function.
        
        :param prefix: Domain separator (0 for nonce, 1 for elements)
        :type prefix: int
        :param b: Element bytes to hash
        :type b: bytes
        :return: Integer hash output
        :rtype: int
        """
        data = bytes([prefix]) + b
        h = hmac.new(self.key, data, digestmod='sha256').digest()
        return int.from_bytes(h, 'big') % (1 << self.m)


    def hash(self, multiset: dict) -> tuple:
        """Compute hash for a multiset.
        
        :param multiset: Dictionary of {element_bytes: multiplicity}
        :type multiset: dict
        :return: Tuple of (XOR_sum, total_count, nonce)
        :rtype: tuple
        """
        h0 = self.H(0, self.nonce)
        sum_xor = h0
        count = 0
        for elem, mult in multiset.items():
            h = self.H(1, elem)
            sum_xor ^= h * (mult % 2)  # Only odd counts affect XOR
            count += mult
        return (sum_xor, count % (1 << self.m), self.nonce)


class MSetAddHash:
    """
    Modular addition-based multiset hash with multiset-collision resistance.
    
    Provides stronger collision resistance than XOR variant at the cost of slightly
    more computation. 
    
    :param key: Secret key for PRF
    :type key: bytes
    :param m: Bit-length for modulus (default 256)
    :type m: int
    """
    
    def __init__(self, key: bytes, m: int = 256):
        """Initialize additive multiset hasher."""
        self.key = key
        self.m = m
        self.nonce = os.urandom(16)

    def H(self, prefix: int, b: bytes) -> int:
        """Internal hash function (same as XORHash)."""
        data = bytes([prefix]) + b
        h = hmac.new(self.key, data, digestmod='sha256').digest()
        return int.from_bytes(h, 'big') % (1 << self.m)

    def hash(self, multiset: dict) -> tuple:
        """Compute additive multiset hash.
        
        :param multiset: Dictionary of {element_bytes: multiplicity}
        :type multiset: dict
        :raises ValueError: If any multiplicity is negative
        :return: Tuple of (modular_sum, nonce)
        :rtype: tuple
        """
        h0 = self.H(0, self.nonce)
        sum_mod = h0
        for elem, mult in multiset.items():
            if mult < 0:
                raise ValueError(f"Negative multiplicity for element {elem}")
            h = self.H(1, elem)
            sum_mod = (sum_mod + h * mult) % (1 << self.m)
        return (sum_mod, self.nonce)


class MSetMuHash:
    """
    Multiplication-based multiset hash using finite field arithmetic.
    
    Provides keyless multiset-collision resistance.
    
    :param q: Prime modulus for finite field (default: 2048-bit prime)
    :type q: int
    """
    def __init__(self, q: int = 2048):
        """Initialize multiplicative hasher."""
        self.q = randprime(2**q, 2**(q+1))

    def H(self, b: bytes) -> int:
        """Hash to field element.
        
        :param b: Element bytes to hash
        :type b: bytes
        :return: Non-zero field element
        :rtype: int
        """
        h = int.from_bytes(sha256(b).digest(), 'big') % self.q
        return h if h != 0 else 1

    def hash(self, multiset: dict) -> int:
        """Compute multiplicative multiset hash.
        
        :param multiset: Dictionary of {element_bytes: multiplicity}
        :type multiset: dict
        :return: Product of hashes raised to multiplicities mod q
        :rtype: int
        """
        product = 1
        for elem, mult in multiset.items():
            h_elem = self.H(elem)
            product = (product * pow(h_elem, mult, self.q)) % self.q
        return product


class MSetVAddHash:
    """Vector additive hash modulo n.
    
    :param n: Modulus for vector components (default 2^16)
    :type n: int
    :param l: Vector length/dimension (default 16)
    :type l: int
    """
    def __init__(self, n: int = 2**16, l: int = 16):
        """Initialize vector additive hasher."""
        self.n = n
        self.l = l

    def H(self, b: bytes) -> list:
        """Map element to vector in Z_n^l.
        
        :param b: Element bytes to hash
        :type b: bytes
        :return: Vector of l integers modulo n
        :rtype: list
        """
        h = sha256(b).digest()
        return [int.from_bytes(h[i*4:(i+1)*4], 'big') % self.n 
                for i in range(self.l)]

    def hash(self, multiset: dict) -> list:
        """
        Compute vector additive hash.
        
        :param multiset: Dictionary of {element_bytes: multiplicity}
        :type multiset: dict
        :return: Sum vector of l components modulo n
        :rtype: list
        """
        sum_vector = [0] * self.l
        for elem, mult in multiset.items():
            vec = self.H(elem)
            for i in range(self.l):
                sum_vector[i] = (sum_vector[i] + vec[i] * mult) % self.n
        return sum_vector
