"""
A Python implementation of incremental multiset hash functions.
"""
import hmac
import hashlib
import secrets

from sympy import randprime
from collections import Counter


def list_to_multiset(lst: list) -> dict:
    """
    Converts a list of elements to a multiset dict where
    each key maps to its multiplicity (number of occurrences).

    :param lst: The list to convert.
    """
    return dict(Counter(lst))


class MSetXORHash:
    """
    Implements the MSet-XOR-Hash scheme.

    - B is the set of distinct elements in the multiset M.
    - M_b is the multiplicity of element b.
    - r is a random nonce (stored in self.nonce).
    - H_K is realized here via an HMAC with key = K and a single-byte prefix.
    """
    def __init__(self, key: bytes = None, m: int = 256, nonce: int = None):
        """
        :param key:  The secret key for HMAC (the 'K' in H_K).
        :param m:    The number of bits for the mod-sum of multiplicities.
                     Also effectively the output size of H_K, truncated if needed.
        """
        if key is None:
            key = secrets.token_bytes(32)

        self.key = key
        self.m = m

        if nonce is None:
            nonce = secrets.token_bytes(16)

        self.nonce = nonce

        # Seed the XOR aggregator with H_K(0, r)
        self.xor_aggregator = self._H(0, self.nonce)
        # Keep a running total of multiplicities (mod 2^m)
        self.total_count = 0

    def _H(self, prefix: int, data: bytes) -> int:
        """
        Realize H_K(prefix, data) via HMAC-SHA256, truncated to m bits if m < 256.
        Returns an integer in [0, 2^m).
        """
        raw = hmac.new(self.key, bytes([prefix]) + data, hashlib.sha256).digest()
        val = int.from_bytes(raw, 'big')
        if self.m < 256:
            val = val % (1 << self.m)
        return val

    def update(self, element: bytes, multiplicity: int = 1):
        """
        Process 'element' with the specified multiplicity in the multiset.

        - For the XOR aggregator, we only add H_K(1, element) if multiplicity is odd.
        - We also add multiplicity to the total_count (mod 2^m).
        """
        if multiplicity < 0:
            raise ValueError("Multiplicity cannot be negative.")

        # XOR aggregator gets toggled only if multiplicity is odd
        if (multiplicity % 2) == 1:
            self.xor_aggregator ^= self._H(1, element)

        # Add multiplicities to total count mod 2^m
        self.total_count = (self.total_count + multiplicity) % (1 << self.m)

    def digest(self) -> tuple:
        """
        Returns a tuple:
          ( xor_aggregator, total_count (mod 2^m), nonce ).
        This exactly matches the structure in the paper's formula.
        """
        return (
            self.xor_aggregator,
            self.total_count,
            self.nonce
        )

    def hash(self, multiset: dict) -> tuple:
        """
        Compute the MSet-XOR-Hash for a given dict-based multiset
        (element -> multiplicity) WITHOUT disturbing the current object's state.

        In effect, this does what the paper calls H_K(M).
        """
        temp = MSetXORHash(self.key, self.m, nonce=self.nonce)

        # Update with each element
        for elem, mult in multiset.items():
            temp.update(elem, mult)

        return temp.digest()


class MSetAddHash:
    """
    Modular addition-based multiset hash (Corollary 2 from the paper),
    with a PRF H_K:{0,1}×B -> Z_{2^m} realized by HMAC-SHA256 truncated to m bits.
    
    Now supports incremental .update() calls:
      - We keep an internal accumulator 'self.acc'
      - Each .update(elem, mult) modifies that accumulator
      - .digest() returns the final (acc, nonce)
    """
    def __init__(self, key: bytes = None, m: int = 256):
        """
        :param key: Secret key for HMAC (the PRF's key).
        :param m:   Bit-length for the modulus (default 256).
        """
        if key is None:
            key = secrets.token_bytes(32)
            
        self.key = key
        self.m = m
        # r in the paper: a random nonce of 16 bytes (128 bits).
        self.nonce = secrets.token_bytes(16)

        # Initialize the accumulator with H_K(0, nonce)
        self.acc = self._H(0, self.nonce)

    def _H(self, prefix: int, data: bytes) -> int:
        """
        Implements H_K(prefix, data) by HMAC-SHA256(key, prefix||data),
        truncated to m bits if m < 256.
        """
        raw = hmac.new(self.key, bytes([prefix]) + data, hashlib.sha256).digest()
        val = int.from_bytes(raw, 'big')
        if self.m < 256:
            val %= (1 << self.m)
        return val

    def update(self, element: bytes, multiplicity: int = 1):
        """
        Incrementally incorporate 'multiplicity' copies of 'element'
        into the current add-hash.

        If multiplicity is negative, this effectively "removes" elements
        (though you must decide if negative totals are allowed).
        
        This operation is O(1) + HMAC overhead (no iteration over the entire multiset).
        """
        if multiplicity == 0:
            return
        if multiplicity < 0:
            # You *can* allow negative updates, as a design choice.
            # Just be consistent about whether the final "multiset" can go negative.
            # We do not raise an error by default, but you can if you want.
            pass

        # The PRF value for 'element'
        h_elem = self._H(1, element)
        # Weighted contribution
        delta = (h_elem * multiplicity) % (1 << self.m)
        # Add to the accumulator
        self.acc = (self.acc + delta) % (1 << self.m)

    def digest(self) -> tuple:
        """
        Returns the final 2-tuple: (acc, nonce).

        Where 'acc' = H_K(0, nonce) + Σ( multiplicity * H_K(1, elem ) ) mod 2^m
        up to this point, through all .update() calls.
        """
        return (self.acc, self.nonce)

    def hash(self, multiset: dict) -> tuple:
        """
        One-shot approach: build an Add-Hash for the given multiset
        *without* disturbing this object's current incremental state.

        - We create a temporary MSetAddHash with the same key & nonce.
        - We do the required .update() calls on that temp object.
        - Then return the final (sum_mod, nonce).
        """
        temp = MSetAddHash(self.key, self.m)
        # Overwrite the random nonce that temp generated with *our* nonce
        temp.nonce = self.nonce
        # Re-seed the accumulator so it uses the same nonce
        temp.acc = temp._H(0, temp.nonce)

        # Now incorporate the dictionary-based multiset
        for elem, mult in multiset.items():
            if mult < 0:
                raise ValueError(f"Negative multiplicity: {mult} for {elem}")
            temp.update(elem, mult)

        return temp.digest()


class MSetMuHash:
    """
    Implements MSet-Mu-Hash in a prime field GF(q) as:
        H(M) = ∏_{b in B} [ H(b ) ^ M_b ] (mod q),
    where H : B -> GF(q)* (the multiplicative group) is realized
    by taking SHA-256(element) mod (q-1), then adding 1 so as
    never to produce 0.

    Paper reference: see Eq.(1),
      H(M) = ∏_{b in B} H(b)^{M_b} in GF(q).

    Usage:
      1) Choose a (large) prime q, pass to constructor.
      2) If needed, check that q-1 is large enough for your security.
      3) The .hash() method returns an integer in [1..q-1].
    """
    def __init__(self, q: int = None, param: int = 2048):
        """
        :param q: A prime (or prime power) used as the field modulus.
                  For real security, q should be large.
        """
        self.q = q or randprime(2**param, 2**(param+1))
        
    def _H(self, data: bytes) -> int:
        """
        Unkeyed function for the element data:
          1) Compute SHA256(data)
          2) Convert to integer
          3) Reduce mod (q-1) and add 1 => in [1..q-1]
        This ensures we never produce 0, thus always a valid nonzero
        element in GF(q).

        If you prefer to allow 0, you can do '% q' instead of '% (q-1)+1.
        """
        raw = hashlib.sha256(data).digest()
        val = int.from_bytes(raw, 'big')
        # map into 1..q-1
        return (val % (self.q - 1)) + 1

    def hash(self, multiset: dict[bytes, int]) -> int:
        """
        Compute the multiplicative multiset hash:
            Π_{b} [ H(b) ^ M_b ] mod q

        :param multiset: dict mapping element -> integer multiplicity.
        :return: an integer in [1..q-1] (unless multiset is empty or all M_b=0).
        """
        product = 1
        for elem, count in multiset.items():
            if count < 0:
                raise ValueError(f"Negative multiplicity {count} for {elem}")
            if count == 0:
                continue
            hval = self._H(elem)
            # compute hval^count mod q
            power = pow(hval, count, self.q)
            # multiply into the running product mod q
            product = (product * power) % self.q

        return product


class MSetVAddHash:
    """
    Implements H(M) = Σ_{b in B} [ M_b * H(b ) ] mod n
    """
    def __init__(self, n: int = 2**128):
        """
        :param n: Modulus (an integer), e.g. 2^m for some m.
        """
        self.n = n
        # We'll store the running sum (Σ M_b * H(b)) mod n
        self.acc = 0
        # If you want to track how many elements total, do so here:
        self.total_count = 0

    def _H(self, element: bytes) -> int:
        """
        An unkeyed map: H: B -> Z_n. You could do a secure hash
        like SHA256(element), then reduce mod n.  The paper does
        mention that H should be a cryptographically strong function.
        """
        raw = hashlib.sha256(element).digest()
        val = int.from_bytes(raw, 'big')
        return val % self.n

    def update(self, element: bytes, multiplicity: int):
        """
        Incrementally add 'multiplicity' copies of 'element'.
        """
        hval = self._H(element)
        delta = (hval * multiplicity) % self.n
        self.acc = (self.acc + delta) % self.n
        self.total_count += multiplicity

        if self.total_count < 0:
            raise ValueError("Total count went negative — too many removes.")

    def digest(self) -> int:
        """
        Return the integer in [0, n-1], i.e. the sum mod n.
        This matches the exact formula Σ M_b * H(b) mod n.
        """
        return self.acc

    def hash(self, multiset: dict[bytes,int]) -> int:
        """
        One-shot approach: compute Σ M_b * H(b) mod n from scratch,
        ignoring any incremental state in this object.
        """
        tmp = 0
        for e, m in multiset.items():
            if m < 0:
                raise ValueError("Negative multiplicity not allowed by default.")
            hval = self._H(e)
            tmp = (tmp + (hval * m)) % self.n
        return tmp

Hasher = MSetAddHash
