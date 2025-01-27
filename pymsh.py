"""
A Python implementation of several incremental multiset hash functions.

Each class implements a different multiset hash scheme:

1. MSetXORHash  : XOR-based incremental hash (using a keyed HMAC-SHA256).
2. MSetAddHash  : Addition-based incremental hash (Corollary 2 in Clarke et al.).
3. MSetMuHash   : Multiplicative hash over a prime field GF(q).
4. MSetVAddHash : Unkeyed, integer addition-based hash mod n.
"""
import hmac
import hashlib
import secrets

from sympy import randprime
from collections import Counter


def list_to_multiset(lst: list) -> dict:
    """
    Convert a list of elements into a dictionary-based multiset.

    :param lst: The list whose elements are to be turned into a multiset.
    :type lst: list
    :return: Dictionary mapping each distinct list element to its multiplicity.
    :rtype: dict

    .. code-block:: python

       >>> list_to_multiset(["apple", "banana", "apple"])
       {'apple': 2, 'banana': 1}
    """
    return dict(Counter(lst))


class MSetXORHash:
    """
    Implements an XOR-based incremental multiset hash (MSet-XOR-Hash).

    The approach is defined as:

    .. math::

        H(M) = (\\oplus_{b : M_b \\text{ is odd}} H_K(1, b)) \\\Vert (\\sum_b M_b \\mod 2^m) \\\Vert (\\text{nonce})

    where :math:`H_K` is a keyed HMAC-SHA256 truncated to :math:`m` bits if necessary.

    :var key: The secret key for HMAC (the 'K' in H_K).
    :vartype key: bytes
    :var m: The bit-size for truncating outputs and for total multiplicity counts.
    :vartype m: int
    :var nonce: A random nonce to ensure uniqueness.
    :vartype nonce: bytes
    :var xor_aggregator: Internal XOR aggregator state.
    :vartype xor_aggregator: int
    :var total_count: Running total of element multiplicities modulo :math:`2^m`.
    :vartype total_count: int
    """

    def __init__(self, key: bytes = None, m: int = 256, nonce: bytes = None):
        """
        Initialize the MSetXORHash.

        :param key: The secret key for HMAC (H_K). If None, a 32-byte key is generated.
        :type key: bytes, optional
        :param m: The number of bits for truncation and mod-sum of multiplicities, defaults to 256.
        :type m: int, optional
        :param nonce: Random nonce for domain separation; if None, a 16-byte nonce is generated.
        :type nonce: bytes, optional
        """
        if key is None:
            key = secrets.token_bytes(32)

        self.key = key
        self.m = m

        if nonce is None:
            nonce = secrets.token_bytes(16)
        self.nonce = nonce

        # Seed the XOR aggregator with H_K(0, nonce)
        self.xor_aggregator = self._H(0, self.nonce)

        # Keep a running total of multiplicities (mod 2^m)
        self.total_count = 0

    def _H(self, prefix: int, data: bytes) -> int:
        """
        Compute :math:`H_K(prefix, data)`, truncated to :math:`m` bits.

        :param prefix: A single-byte prefix (0 or 1 in common usage).
        :type prefix: int
        :param data: Data to be hashed.
        :type data: bytes
        :return: The HMAC-SHA256 output as an integer in [0, :math:`2^m - 1`].
        :rtype: int
        """
        raw = hmac.new(self.key, bytes([prefix]) + data, hashlib.sha256).digest()
        val = int.from_bytes(raw, 'big')
        if self.m < 256:
            val %= (1 << self.m)
        return val

    def update(self, element: bytes, multiplicity: int = 1):
        """
        Incrementally update the hash with `multiplicity` copies of `element`.

        :param element: Element to be added or removed.
        :type element: bytes
        :param multiplicity: Number of times the element is present (or removed if you track negatives).
                             Must be non-negative in this class.
        :type multiplicity: int
        :raises ValueError: If `multiplicity` is negative.
        """
        if multiplicity < 0:
            raise ValueError("Multiplicity cannot be negative.")

        # XOR aggregator toggled only if multiplicity is odd
        if (multiplicity % 2) == 1:
            self.xor_aggregator ^= self._H(1, element)

        # Update total_count mod 2^m
        self.total_count = (self.total_count + multiplicity) % (1 << self.m)

    def digest(self) -> tuple:
        """
        Produce the current digest.

        :return: A tuple (xor_aggregator, total_count, nonce).
        :rtype: (int, int, bytes)
        """
        return self.xor_aggregator, self.total_count, self.nonce

    def hash(self, multiset: dict) -> tuple:
        """
        One-shot computation of the MSet-XOR-Hash for `multiset`, ignoring current state.

        :param multiset: A dict mapping elements to their multiplicities.
        :type multiset: dict[bytes, int]
        :return: The computed hash tuple (xor_aggregator, total_count, nonce).
        :rtype: (int, int, bytes)
        """
        temp = MSetXORHash(self.key, self.m, nonce=self.nonce)
        for elem, mult in multiset.items():
            temp.update(elem, mult)
        return temp.digest()


class MSetAddHash:
    """
    Addition-based incremental multiset hash in :math:`Z_{2^m}`.

    This corresponds to Corollary 2 in the reference paper:

    .. math::

        H(M) = H_K(0, nonce) + \\sum_{b} \\bigl(M_b * H_K(1, b)\\bigr) \\mod 2^m

    :var key: Secret key for HMAC-based PRF.
    :vartype key: bytes
    :var m: Bit-length for the modulus :math:`2^m`.
    :vartype m: int
    :var nonce: 16-byte random nonce for domain separation.
    :vartype nonce: bytes
    :var acc: Internal accumulator representing the incremental hash state.
    :vartype acc: int
    """

    def __init__(self, key: bytes = None, m: int = 256):
        """
        Initialize MSetAddHash.

        :param key: Secret key (32 bytes if None, auto-generated).
        :type key: bytes, optional
        :param m: Bit-length for modulus :math:`2^m`, defaults to 256.
        :type m: int, optional
        """
        if key is None:
            key = secrets.token_bytes(32)
        self.key = key
        self.m = m

        # Random nonce (16 bytes)
        self.nonce = secrets.token_bytes(16)

        # Seed the accumulator with H_K(0, nonce)
        self.acc = self._H(0, self.nonce)

    def _H(self, prefix: int, data: bytes) -> int:
        """
        PRF: :math:`H_K(prefix, data) = \\text{HMAC-SHA256} (key, prefix||data)`, truncated to :math:`m` bits.

        :param prefix: Single byte prefix (e.g., 0 or 1).
        :type prefix: int
        :param data: Data to hash.
        :type data: bytes
        :return: The integer result in [0, :math:`2^m - 1`].
        :rtype: int
        """
        raw = hmac.new(self.key, bytes([prefix]) + data, hashlib.sha256).digest()
        val = int.from_bytes(raw, 'big')
        if self.m < 256:
            val %= (1 << self.m)
        return val

    def update(self, element: bytes, multiplicity: int = 1):
        """
        Incrementally add `multiplicity` copies of `element`.

        :param element: The element (byte string).
        :type element: bytes
        :param multiplicity: How many times to add this element.
                             May be negative if removal is allowed by your design.
        :type multiplicity: int
        """
        if multiplicity == 0:
            return

        h_elem = self._H(1, element)
        delta = (h_elem * multiplicity) % (1 << self.m)
        self.acc = (self.acc + delta) % (1 << self.m)

    def digest(self) -> tuple:
        """
        Return the current hash state and nonce.

        :return: (acc, nonce)
        :rtype: (int, bytes)
        """
        return self.acc, self.nonce

    def hash(self, multiset: dict) -> tuple:
        """
        One-shot hash of a multiset, ignoring the current incremental state.

        :param multiset: A dictionary mapping elements to multiplicities.
        :type multiset: dict[bytes, int]
        :return: (sum_mod_2m, nonce)
        :rtype: (int, bytes)
        :raises ValueError: If any multiplicity is negative, in this default policy.
        """
        temp = MSetAddHash(self.key, self.m)
        temp.nonce = self.nonce
        temp.acc = temp._H(0, temp.nonce)

        for elem, mult in multiset.items():
            if mult < 0:
                raise ValueError(f"Negative multiplicity: {mult} for element {elem}")
            temp.update(elem, mult)

        return temp.digest()


class MSetMuHash:
    """
    Multiplicative multiset hash over a prime field :math:`GF(q)`.

    .. math::

        H(M) = \\prod_{b \\in M} \\bigl( H(b) \\bigr)^{M_b} \\mod q

    where :math:`H(b)` is an unkeyed map from :math:`b` to :math:`GF(q)^*`.

    :var q: Prime modulus for the field :math:`GF(q)`.
    :vartype q: int
    """

    def __init__(self, q: int = None, param: int = 2048):
        """
        Initialize MSetMuHash.

        :param q: Prime modulus. If None, a ~2048-bit prime is generated.
        :type q: int, optional
        :param param: Bit-length of the prime if generated, defaults to 2048.
        :type param: int, optional
        """
        self.q = q or randprime(2**param, 2**(param + 1))

    def _H(self, data: bytes) -> int:
        """
        Map data to :math:`[1..q-1]`.

        .. math::

            \\text{_H}(data) = (\\text{SHA256}(data) \\mod (q-1)) + 1

        :param data: The element to be hashed.
        :type data: bytes
        :return: An integer in :math:`[1..q-1]`.
        :rtype: int
        """
        raw = hashlib.sha256(data).digest()
        val = int.from_bytes(raw, 'big')
        return (val % (self.q - 1)) + 1

    def hash(self, multiset: dict) -> int:
        """
        Compute the multiplicative hash of `multiset` in :math:`GF(q)`.

        :param multiset: Dict mapping elements to their multiplicities.
        :type multiset: dict[bytes, int]
        :return: The product of :math:`H(elem)^{count}` modulo :math:`q`.
        :rtype: int
        :raises ValueError: If any multiplicity is negative.
        """
        product = 1
        for elem, count in multiset.items():
            if count < 0:
                raise ValueError(f"Negative multiplicity {count} for {elem}")
            if count == 0:
                continue
            hval = self._H(elem)
            product = (product * pow(hval, count, self.q)) % self.q
        return product


class MSetVAddHash:
    """
    Unkeyed, integer-based additive multiset hash modulo `n`.

    .. math::

        H(M) = \\sum_{b \\in M} \\bigl( M_b * H(b) \\bigr) \\mod n

    where :math:`H(b)` is unkeyed, such as :math:`H(b) = \\text{SHA256}(b) \\mod n`.

    :var n: Modulus (e.g. :math:`2^m`).
    :vartype n: int
    :var acc: Internal accumulator for incremental hashing.
    :vartype acc: int
    :var total_count: Running total of all multiplicities.
    :vartype total_count: int
    """

    def __init__(self, n: int = 2**128):
        """
        Initialize MSetVAddHash.

        :param n: Modulus for additions, defaults to :math:`2^{128}`.
        :type n: int, optional
        """
        self.n = n
        self.acc = 0
        self.total_count = 0

    def _H(self, element: bytes) -> int:
        """
        Map an element to :math:`[0..n-1]`.

        .. math::

            \\text{_H}(element) = \\text{SHA256}(element) \\mod n

        :param element: The element as bytes.
        :type element: bytes
        :return: The result in [0, n-1].
        :rtype: int
        """
        raw = hashlib.sha256(element).digest()
        val = int.from_bytes(raw, 'big')
        return val % self.n

    def update(self, element: bytes, multiplicity: int):
        """
        Incrementally add `multiplicity` copies of `element`.

        :param element: Element to be hashed.
        :type element: bytes
        :param multiplicity: Number of copies to add (or remove if negative).
        :type multiplicity: int
        :raises ValueError: If total_count becomes negative.
        """
        hval = self._H(element)
        delta = (hval * multiplicity) % self.n
        self.acc = (self.acc + delta) % self.n
        self.total_count += multiplicity

        if self.total_count < 0:
            raise ValueError("Total count went negative — too many removes.")

    def digest(self) -> int:
        """
        Return the accumulated hash value (mod `n`).

        :return: The sum modulo `n`.
        :rtype: int
        """
        return self.acc

    def hash(self, multiset: dict) -> int:
        """
        One-shot computation ignoring the current internal state.

        :param multiset: Dictionary mapping elements to multiplicities.
        :type multiset: dict[bytes, int]
        :return: Sum of `multiplicity * H(element)` mod n.
        :rtype: int
        :raises ValueError: If a negative multiplicity is encountered.
        """
        tmp = 0
        for e, m in multiset.items():
            if m < 0:
                raise ValueError("Negative multiplicity not allowed by default.")
            hval = self._H(e)
            tmp = (tmp + (hval * m)) % self.n
        return tmp


#: By default, export a convenient alias.
Hasher = MSetAddHash
