import hashlib
import hmac

from .base import MSH
from secrets import token_bytes

class XORMSH(MSH):
    def __init__(self, key_size=64, nonce_size=16):
        """
        Initialises the XOR-based multiset hashing (MSH) class.

        Keeps track of a combined hash value for making
        incremental updates later using `update(...)`.

        The Clarke et al. MSet-XOR-Hash scheme requires a
        key for an HMAC application of size `key_size`.
        """
        super().__init__()
        self.K = token_bytes(key_size)
        self.nonce = token_bytes(nonce_size)

        # This convolution is needed because byte arrays
        # in Python are immutable.
        self.init_hmac = int.from_bytes(
            hmac.new(self.K, self.nonce, hashlib.blake2b).digest(),
            byteorder='big')
        self.combined_hash = self.init_hmac


    def reset(self):
        """
        Reset the combined hash value, allowing `update(...)`
        to be used afresh.
        """
        self.combined_hash = self.init_hmac


    def __combine(self, new_hash):
        """
        Combines the existing combined hash, `self.combined_hash`,
        with a new hash.

        Parameters:
            new_hash : The input hash to newly combine.
        """
        self.combined_hash ^= int.from_bytes(new_hash, byteorder='big')
        return self.combined_hash.to_bytes(
            (self.combined_hash.bit_length() + 7) // 8, byteorder='big')


    def hash(self, elements):
        """
        Hash a list of elements.

        Parameters:
            elements : List of elements.
        """
        for e in elements:
            self.__combine(super().hash_element(e))
        # Return the final combined hash
        return self.H(self.__combine(bytes())).digest()


    def update(self, new_element):
        """
        Updates an existing combined hash value with a new element.

        Parameters:
            new_element : New element to add to the MSH.
        """
        return self.H(self.__combine
                      (super().hash_element(new_element))).digest()
