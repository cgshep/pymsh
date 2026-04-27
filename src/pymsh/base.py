import hashlib

class MSH:
    def __init__(self, hash_func=hashlib.blake2b):
        """
        Initialises the multiset hashing (MSH) class.

        One can specify one's own hash function with `hash_func`.

        Parameters:
            hash_func : Hash function to use. Default uses BLAKE2b
        """
        self.H = hash_func


    def hash_element(self, e):
        """
        Hash an element using the hash function in `self.H`.

        Parameters:
            e : Element to hash
        """
        return self.H(e).digest()
