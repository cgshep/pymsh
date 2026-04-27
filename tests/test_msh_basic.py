import pytest

from pymsh.xormsh import XORMSH
from utils import map_str_bytes

@pytest.mark.parametrize("msh_class", [XORMSH])
class TestBasic:
    v1 = map_str_bytes(["apple", "banana", "cranberry", "date"])
    def test_basic_equiv(self, msh_class):
        msh = msh_class()
        v2 = self.v1
        h1 = msh.hash(self.v1)
        msh.reset()
        h2 = msh.hash(v2)
        msh.reset()
        assert h1 == h2

    def test_basic_empty(self, msh_class):
        msh = msh_class()
        v2 = v3 = []
        h1 = msh.hash(v2)
        msh.reset()
        h2 = msh.hash(v3)
        msh.reset()
        # MSH([]) == MSH([])
        assert h1 == h2

    def test_basic_one_empty(self, msh_class):
        msh = msh_class()
        v2 = []
        h1 = msh.hash(self.v1)
        msh.reset()
        h2 = msh.hash(v2)
        msh.reset()
        assert h1 != h2

    def test_basic_reordered(self, msh_class):
        v2 = map_str_bytes(["date", "banana", "cranberry", "apple"])
        msh = XORMSH()
        h1 = msh.hash(self.v1)
        msh.reset()
        h2 = msh.hash(v2)
        msh.reset()
        assert h1 == h2

    def test_xormsh_update(self, msh_class):
        v2 = []
        msh = msh_class()
        h1 = msh.hash(self.v1)
        msh.reset()
        h2 = msh.hash(v2)
        msh.update(b"date")
        msh.update(b"banana")
        msh.update(b"cranberry")
        h2 = msh.update(b"apple")
        msh.reset()
        assert h1 == h2

    def test_basic_two_update(self, msh_class):
        """
        Testing two empty inputs; the hashes are updated
        using the same elements in different orders.
        """
        msh = msh_class()
        h1 = msh.hash([])
        msh.update(b"apple")
        msh.update(b"date")
        msh.update(b"cranberry")
        h1 = msh.update(b"banana")
        msh.reset()
        h2 = msh.hash([])
        msh.update(b"date")
        msh.update(b"banana")
        msh.update(b"cranberry")
        h2 = msh.update(b"apple")
        msh.reset()
        assert h1 == h2
