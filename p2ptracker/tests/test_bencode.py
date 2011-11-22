__author__ = 'ramon'


from p2ptracker.bencode import bencode
from p2ptracker import create_app
from flaskext.testing import TestCase

class TestBencode(TestCase):

    def create_app(self):
        return create_app()

    def test_integer(self):
        assert bencode(4) == 'i4e'
        assert bencode(0) == 'i0e'
        assert bencode(-10) == 'i-10e'
        assert bencode(12345678901234567890L) == 'i12345678901234567890e'

    def test_string(self):
        assert bencode('') == '0:'
        assert bencode('abc') == '3:abc'
        assert bencode('1234567890') == '10:1234567890'

    def test_list(self):
        assert bencode([]) == 'le'
        assert bencode([1, 2, 3]) == 'li1ei2ei3ee'
        assert bencode([['Alice', 'Bob'], [2, 3]]) == 'll5:Alice3:Bobeli2ei3eee'

    def test_dict(self):
        assert bencode({}) == 'de'
        assert bencode({'age': 25, 'eyes': 'blue'}) == 'd3:agei25e4:eyes4:bluee'
        assert bencode({'spam.mp3': {'author': 'Alice', 'length': 100000}}) == 'd8:spam.mp3d6:author5:Alice6:lengthi100000eee'

    def test_fail_integerkeyed_dict(self):
        try:
            bencode({1: 'foo'})
            assert False
        except AssertionError:
            pass
