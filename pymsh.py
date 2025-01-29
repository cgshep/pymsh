"""
A Python implementation of several incremental multiset hash functions.

Each class implements a different multiset hash scheme:

1. MSetXORHash  : XOR-based incremental hash (using a keyed HMAC-BLAKE2b).
2. MSetAddHash  : Additive incremental hash (Cor. 2 in Clarke et al.)
3. MSetMuHash   : Multiplicative hash over a prime field GF(q).
4. MSetVAddHash : Unkeyed, integer addition-based hash mod n.
"""
import hmac
import hashlib
import secrets

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

    :var key: The secret key for HMAC (the 'K' in H_K).
    :vartype key: bytes
    :var m: Bit-size for truncating outputs and for total multiplicity counts.
    :vartype m: int
    :var nonce: A random nonce to ensure uniqueness.
    :vartype nonce: bytes
    :var xor_aggregator: Internal XOR aggregator state.
    :vartype xor_aggregator: int
    :var total_count: Total of element multiplicities modulo :math:`2^m`.
    :vartype total_count: int
    """

    def __init__(self, key: bytes = None, m: int = 512, nonce: bytes = None):
        """
        Initialize the MSetXORHash.

        :param key: The HMAC secret key. If None, a 32-byte key is generated.
        :type key: bytes, optional
        :param m: The number of bits for truncation and mod-sum of
                  multiplicities, defaults=512
        :type m: int, optional
        :param nonce: Random nonce; if None, a 16-byte one is generated.
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
        :return: The HMAC-BLAKE3 output as an integer in [0, :math:`2^m - 1`].
        :rtype: int
        """
        raw = hmac.new(self.key, bytes([prefix]) + data,
                       hashlib.blake2b).digest()
        val = int.from_bytes(raw, 'big')
        if self.m < 512:
            val %= (1 << self.m)
        return val

    def update(self, element: bytes, multiplicity: int = 1):
        """
        Incrementally update the hash with `multiplicity` copies of `element`.

        :param element: Element to be added or removed.
        :type element: bytes
        :param multiplicity: # times element is present.
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
        One-shot computation of the MSet-XOR-Hash for `multiset`,
        ignoring current state.

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

        H(M) = H_K(0, nonce) + \\sum_{b} \\bigl(
                   M_b * H_K(1, b)\\bigr) \\mod 2^m

    :var key: Secret key for HMAC-based PRF.
    :vartype key: bytes
    :var m: Bit-length for the modulus :math:`2^m`.
    :vartype m: int
    :var nonce: 16-byte random nonce for domain separation.
    :vartype nonce: bytes
    :var acc: Internal accumulator representing the incremental hash state.
    :vartype acc: int
    """

    def __init__(self, key: bytes = None, m: int = 512, nonce: bytes = None):
        """
        Initialize MSetAddHash.

        :param key: Secret key (32 bytes if None, auto-generated).
        :type key: bytes, optional
        :param m: Bit-length for modulus :math:`2^m`, defaults to 512.
        :type m: int, optional
        :param none: Random 16-byte nonce.
        :type m: bytes, optional
        """
        if key is None:
            key = secrets.token_bytes(32)
        self.key = key
        self.m = m

        # Random nonce (16 bytes)
        if nonce is None:
            nonce = secrets.token_bytes(16)
        self.nonce = nonce

        # Seed the accumulator with H_K(0, nonce)
        self.acc = self._H(0, self.nonce)

    def _H(self, prefix: int, data: bytes) -> int:
        """
        Internal PRF
        :math:`H_K(prefix, data) = \\text{HMAC-BLAKE2b} (key, prefix||data)`,
        truncated to :math:`m` bits.

        :param prefix: Single byte prefix (e.g., 0 or 1).
        :type prefix: int
        :param data: Data to hash.
        :type data: bytes
        :return: The integer result in [0, :math:`2^m - 1`].
        :rtype: int
        """
        raw = hmac.new(self.key, bytes([prefix]) + data,
                       hashlib.blake2b).digest()
        val = int.from_bytes(raw, 'big')
        if self.m < 512:
            val %= (1 << self.m)
        return val

    def update(self, element: bytes, multiplicity: int = 1):
        """
        Incrementally add `multiplicity` copies of `element`.

        :param element: The element (byte string).
        :type element: bytes
        :param multiplicity: How many times to add this element.
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
        :raises ValueError: If any multiplicity is negative.
        """
        temp = MSetAddHash(self.key, self.m)
        temp.nonce = self.nonce
        temp.acc = temp._H(0, temp.nonce)

        for elem, mult in multiset.items():
            if mult < 0:
                raise ValueError(
                    f"Negative multiplicity: {mult} for element {elem}")
            temp.update(elem, mult)

        return temp.digest()


# Public modulus for GF(q)
public_q = int("6652616640577475268971429076805625149913200"
               "7237473929971857046929191916395473010413181"
               "6921905009274874106841977276958382342329138"
               "7880913720094685938088211204127144470701045"
               "8217504597989486041057295615582023840660640"
               "6736946360571391328394114493744144145174864"
               "9425911675412818184664932340809747718924170"
               "2922582870945918553504431971919931032027568"
               "0445554556187296740996375234558154304451216"
               "0125651485262551934525973355751189002994750"
               "3856216983840057848720320051096475399402402"
               "5078330763094914973367247392698481186069677"
               "7424080627152889650559503455254791753121600"
               "2880701566372634548740195419114055944960856"
               "9374555581149023077545834570641481012491106"
               "7171107311501557718711966052508420204852872"
               "5781421047435505552487306272127367079188222"
               "6249240792539422214906922905377456006121111"
               "6959272952284971420972177813441764061521154"
               "2964437706121614548953434806289746488448383"
               "6757180885372769479907419744068216269151011"
               "3219811148336988874037")


class MSetMuHash:
    """
    Multiplicative multiset hash over a prime field :math:`GF(q)`.

    .. math::

        H(M) = \\prod_{b \\in M} \\bigl( H(b) \\bigr)^{M_b} \\mod q

    where :math:`H(b)` is an unkeyed map from :math:`b` to :math:`GF(q)^*`.

    :var q: Prime modulus for the field :math:`GF(q)`.
    :vartype q: int
    """

    def __init__(self, q: int = None):
        """
        Initialize MSetMuHash.

        :param q: Prime modulus. If None, a ~2048-bit prime is generated.
        :type q: int, optional
        """
        self.q = q or public_q

    def _H(self, data: bytes) -> int:
        """
        Map data to :math:`[1..q-1]`.

        .. math::

            \\text{_H}(data) = (\\text{BLAKE2b}(data) \\mod (q-1)) + 1

        :param data: The element to be hashed.
        :type data: bytes
        :return: An integer in :math:`[1..q-1]`.
        :rtype: int
        """
        raw = hashlib.blake2b(data).digest()
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

    where :math:`H(b)` is unkeyed, such as
    :math:`H(b) = \\text{BLAKE2b}(b) \\mod n`.

    :var n: Modulus (e.g. :math:`2^m`).
    :vartype n: int
    :var acc: Internal accumulator for incremental hashing.
    :vartype acc: int
    :var total_count: Running total of all multiplicities.
    :vartype total_count: int
    """

    def __init__(self, n: int = 2**256):
        """
        Initialize MSetVAddHash.

        :param n: Modulus for additions, defaults to :math:`2^{256}`.
        :type n: int, optional
        """
        self.n = n
        self.acc = 0
        self.total_count = 0

    def _H(self, element: bytes) -> int:
        """
        Map an element to :math:`[0..n-1]`.

        .. math::

            \\text{_H}(element) = \\text{BLAKE2b}(element) \\mod n

        :param element: The element as bytes.
        :type element: bytes
        :return: The result in [0, n-1].
        :rtype: int
        """
        raw = hashlib.blake2b(element).digest()
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
                raise ValueError("Negative multiplicity not allowed.")
            hval = self._H(e)
            tmp = (tmp + (hval * m)) % self.n
        return tmp


#: By default, export a convenient alias.
Hasher = MSetAddHash
