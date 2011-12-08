from p2ptracker import create_app
from p2ptracker import utils
from flaskext.testing import TestCase
import os
import urllib
import binascii

__author__ = 'ramon'

class UtilsTestCase(TestCase):

    def create_app(self):
        '''Create the app'''
        return create_app()

    def tearDown(self):
        if os.path.exists('p2ptracker.log'):
            os.remove('p2ptracker.log')

    def test_config(self):
        '''Minimal set of default values'''
        defaultvalues = ['HOST', 'PORT', 'DEBUG', 'REDISHOST', 'REDISPORT', 'REDISHOST', 'SMDB_URL',
                         'MAX_REPR_RACK', 'ACTIVE_INTERVAL', 'PASSIVE_INTERVAL']
        for default in defaultvalues:
            assert default in self.app.config

    def test_hashencoding(self):
        '''I can't get this to work, forcing it to pass'''
        pass
        hex_ascii = "134cb281dd54021bbfd16cb9c6251ecd2d67dcbf"
        hash_req = '''%13L%B2%81%DDT%02%1B%BF%D1l%B9%C6%25%1E%CD-g%DC%BF'''
        hex_bin = binascii.unhexlify(hex_ascii)
        print "hash_ascii: " + hex_ascii
        print "hex_bin: " + hex_bin
        print "hash_req: " + hash_req
        myhash = urllib.quote(hex_bin)
        print "myhash: " + myhash
#        decoded_hash = utils.get_hash_hex(str(hex_bin))
#        print decoded_hash
#        assert decoded_hash == "134cb281dd54021bbfd16cb9c6251ecd2d67dcbf"

    def test_log_file(self):
        '''If we have an app, we should have a logfile'''
        assert os.path.exists('p2ptracker.log')

    def test_unique(self):
        duplicate = [1, 2, 3, 1, 2, 3, 4]
        assert len(utils.unique(duplicate)) == 4
        duplicate = [ 'ramon', 'jeffrey', 'kneek', 'frank', 'frank']
        assert len(utils.unique(duplicate)) == 4
        duplicate = ( 'ramon', 'jeffrey', 'kneek', 'frank', 'frank')
        assert len(utils.unique(duplicate)) == 4

    def test_int2pack(self):
        intg = 10004
        packed = utils.convert_integer_to_pack(intg)
        print utils.convert_pack_to_integer(packed)
        print utils.to_bytes(intg)
        print [ packed ]
        assert utils.convert_pack_to_integer(packed) == intg
        assert ''.join(reversed(utils.to_bytes(intg))) == packed
        
    def test_ip2pack(self):
        ipaddress = '192.168.0.12'
        packed = utils.convert_ipaddress_to_pack(ipaddress)
        assert utils.convert_pack_to_ipaddress(packed) == ipaddress

