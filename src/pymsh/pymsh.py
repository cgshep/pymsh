import hashlib

class MSH():
    def __init__(self, hash_func=hashlib.blake2b):
        """
        Initialises the multiset hashing (MSH) class.

        One can specify one's own hash function with `hash_func`.

        Keeps track of a combined hash value for making
        incremental updates later using `update(...)`.

        Parameters:
            hash_func : Hash function to use. Default uses BLAKE2b
        """
        self.H = hash_func
        self.combined_hash = 0


    def reset(self):
        """
        Reset the combined hash value, allowing `update(...)`
        to be used afresh.
        """
        self.combined_hash = 0


    def __hash_element(self, e):
        """
        Hash an element using the hash function specified
        in `__init__(...)`

        Parameters:
            e : Element to hash
        """
        return self.H(e).digest()


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
            self.__combine(self.__hash_element(e))
        # Return the final combined hash
        return self.H(self.__combine(bytes())).digest()


    def update(self, new_element):
        """
        Updates an existing combined hash value with a new element.

        Parameters:
            new_element : New element to add to the MSH.
        """
        return self.H(self.__combine
                      (self.__hash_element(new_element))).digest()
