"""
https://github.com/hyves-org/p2ptracker
Copyright (c) 2011, Ramon van Alteren
MIT license: http://www.opensource.org/licenses/MIT
"""

from flaskext.testing import TestCase
import redis
import logging
from p2ptracker import create_app, utils, bencode
from p2ptracker.tests.helpers import utils as testutils

import os

REMOVE_LOG = False
log = logging.getLogger('hyves.%s' % __name__)
SCRIPTDIR=os.path.dirname(__file__)

class TestAnnounce(TestCase):

    def create_app(self):
        return create_app()

    def setUp(self):
        r = redis.Redis(host = self.app.config['REDISHOST'], port = self.app.config['REDISPORT'])
        r.ping()
        r.flushdb()

    def tearDown(self):
        if os.path.exists('%s/p2ptracker.log' % SCRIPTDIR) and REMOVE_LOG:
            os.remove('%s/p2ptracker.log' % SCRIPTDIR)
        r = redis.Redis(host = self.app.config['REDISHOST'], port = self.app.config['REDISPORT'])
        r.ping()
        r.flushdb()

    def test_active_interval(self):
        """If a transfer is active, client should get the active_interval from tracker"""
        c1 = ('192.168.0.10', 'testrack1')
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        log.debug('using test torrent file: %s' % filename)
        ihash = testutils.get_ihash_from_filename(filename)
        log.debug('ihash: %s' % ihash)
        filesz = testutils.get_size_from_filename(filename)
        resp = testutils.post_torrent(self.client, filename)
        log.debug('resp.data on post: %s' % resp.data)
        resp = testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=filesz)
        self.assert200(resp)
        print bencode.bdecode(resp.data)
        self.assertEqual(bencode.bdecode(resp.data)['interval'], self.app.config['ACTIVE_INTERVAL'])

    def test_active_interval_for_initial_seeder(self):
        """If a transfer is active, client should get the active_interval from tracker"""
        c1 = ('192.168.0.10', 'testrack1')
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = testutils.get_ihash_from_filename(filename)
        testutils.post_torrent(self.client, filename)
        resp = testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=0)
        self.assert200(resp)
        print bencode.bdecode(resp.data)
        self.assertEqual(bencode.bdecode(resp.data)['interval'], self.app.config['ACTIVE_INTERVAL'])

    def test_passive_interval(self):
        """If a transfer is not active, client should get the passive_interval from tracker"""
        c1 = ('192.168.0.10', 'testrack1')
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = testutils.get_ihash_from_filename(filename)
        filesz = testutils.get_size_from_filename(filename)
        resp = testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=filesz)
        self.assert200(resp)
        print bencode.bdecode(resp.data)
        self.assertEqual(bencode.bdecode(resp.data)['interval'], self.app.config['PASSIVE_INTERVAL'])

    def test_peer_doesnot_get_himself(self):
        '''Make sure that the tracker doesn;t return my own ipaddress'''
        ipaddress = '192.168.0.12'
        port = 10004
        rackname = 'FA12'
        left = 0
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = testutils.get_ihash_from_filename(filename)
        testutils.post_torrent(self.client, filename)
        resp = testutils.add_client(self.app, ihash=ihash, ipaddress=ipaddress, rackname=rackname,
                                      left=left, event=None, mock_smdb=True, port=port)
        resp_dict = bencode.bdecode(resp.data)
        print resp_dict
        self.assertEqual(resp_dict['peers'], '')
        self.assertEqual(resp_dict['warning'], '')
        self.assertEqual(resp_dict['interval'], self.app.config['ACTIVE_INTERVAL'])
        self.assert200(resp)

    def test_two_peers_see_each_other(self):
        '''If I announce from two peers,  they should get each other from the tracker'''
        p1_ip = '192.168.0.12'
        p2_ip = '192.168.0.13'
        rack = 'FA12'
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = testutils.get_ihash_from_filename(filename)
        left = testutils.get_size_from_filename(filename)
        testutils.post_torrent(self.client, filename)
        # Init peers with tracker
        testutils.add_client(self.app, ihash=ihash, ipaddress=p1_ip, rackname=rack, left=left, event=None, mock_smdb=True, port=port)
        testutils.add_client(self.app, ihash=ihash, ipaddress=p2_ip, rackname=rack, left=left, event=None, mock_smdb=True, port=port)
        # Get actual peers
        resp_p1 = testutils.add_client(self.app, ihash=ihash, ipaddress=p1_ip, rackname=rack, left=left, event=None, mock_smdb=False, port=port)
        resp_p2 = testutils.add_client(self.app, ihash=ihash, ipaddress=p2_ip, rackname=rack, left=left, event=None, mock_smdb=False, port=port)
        self.assert200(resp_p1)
        self.assert200(resp_p2)
        resp_p1_d = bencode.bdecode(resp_p1.data)
        resp_p2_d = bencode.bdecode(resp_p2.data)
        self.assertEquals(utils.convert_pack_to_ipaddress(resp_p1_d['peers'][:4]), p2_ip)
        self.assertEquals(utils.convert_pack_to_ipaddress(resp_p2_d['peers'][:4]), p1_ip)

    def test_repr_view_from_rack(self):
        '''The first two peers become repr for a rack, after that the next peer should only see rack members'''
        # Set it up
        r1_repr1_ip = '192.168.0.12'
        r1_repr2_ip = '192.168.0.13'
        r1_np1_ip = '192.168.0.14'
        rack1 = 'FA12'
        r2_repr1_ip = '192.168.1.12'
        r2_repr2_ip = '192.168.1.13'
        r2_np1_ip = '192.168.1.14'
        rack2 = 'FA13'
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        left = testutils.get_size_from_filename(filename)
        ihash = testutils.get_ihash_from_filename(filename)
        testutils.post_torrent(self.client, filename)
        r1_peers = [r1_repr1_ip, r1_repr2_ip, r1_np1_ip ]
        r2_peers = [r2_repr1_ip, r2_repr2_ip, r2_np1_ip ] # Order is important here !!
        # Init all peers with the tracker
        for peer in r1_peers:
            testutils.add_client(self.app, ihash=ihash, ipaddress=peer, rackname=rack1, left=left, event=None, mock_smdb=True, port=port)
        for peer in r2_peers:
            testutils.add_client(self.app, ihash=ihash, ipaddress=peer, rackname=rack2, left=left, event=None, mock_smdb=True, port=port)
        # Collect the responses
        r1_resp = r2_resp = {}
        for peer in r1_peers:
            r1_resp[peer] = bencode.bdecode(testutils.add_client(self.app, ihash=ihash, ipaddress=peer, rackname=rack1, left=left, event=None, mock_smdb=True, port=port).data)['peers']
        for peer in r2_peers:
            r2_resp[peer] = bencode.bdecode(testutils.add_client(self.app, ihash=ihash, ipaddress=peer, rackname=rack2, left=left, event=None, mock_smdb=True, port=port).data)['peers']
        # the first repr should see it's own rack + the reprs from the other rack
        self.assertEqual(sorted(utils.get_ips_from_pack(r1_resp[r1_repr1_ip])), sorted([r1_repr2_ip, r1_np1_ip,r2_repr1_ip, r2_repr2_ip]))
        # the second repr should see it's own rack + the reprs from the other rack
        self.assertEqual(sorted(utils.get_ips_from_pack(r1_resp[r1_repr2_ip])), sorted([r1_repr1_ip, r1_np1_ip,r2_repr1_ip, r2_repr2_ip]))
        # the normal peer should see it's own rack reprs only and not the reprs from the other rack
        self.assertEqual(sorted(utils.get_ips_from_pack(r1_resp[r1_np1_ip])), sorted([r1_repr1_ip, r1_repr2_ip]))
        # The same should be true for the other rack
        # the first repr should see it's own rack + the reprs from the other rack
        self.assertEqual(sorted(utils.get_ips_from_pack(r2_resp[r2_repr1_ip])), sorted([r1_repr2_ip, r2_np1_ip,r1_repr1_ip, r2_repr2_ip]))
        # the second repr should see it's own rack + the reprs from the other rack
        self.assertEqual(sorted(utils.get_ips_from_pack(r1_resp[r2_repr2_ip])), sorted([r2_repr1_ip, r2_np1_ip,r1_repr1_ip, r1_repr2_ip]))
        # the normal peer should see it's own rack reprs only and not the reprs from the other rack
        self.assertEqual(sorted(utils.get_ips_from_pack(r1_resp[r2_np1_ip])), sorted([r2_repr1_ip, r2_repr2_ip]))

    def test_seeder_doesnt_get_seeders(self):
        """If a seeder requests peers, he should not get any seeders"""
        c1 = ('192.168.0.10', 'testrack1')
        c2 = ('192.168.0.11', 'testrack2')
        c3 = ('192.168.0.12', 'testrack3')
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = testutils.get_ihash_from_filename(filename)
        filesz = testutils.get_size_from_filename(filename)
        testutils.post_torrent(self.client, filename)
        testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        testutils.add_client(self.app, ihash=ihash, ipaddress=c2[0], rackname=c2[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        testutils.add_client(self.app, ihash=ihash, ipaddress=c3[0], rackname=c3[1], event=None, mock_smdb=True, port=port, left=filesz) # Leecher
        respc1 = testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        respc2 = testutils.add_client(self.app, ihash=ihash, ipaddress=c2[0], rackname=c2[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        respc3 = testutils.add_client(self.app, ihash=ihash, ipaddress=c3[0], rackname=c3[1], event=None, mock_smdb=True, port=port, left=filesz) # Leecher
        self.assertEqual(utils.get_ips_from_pack(bencode.bdecode(respc1.data)['peers']), [ c3[0] ])
        self.assertEqual(utils.get_ips_from_pack(bencode.bdecode(respc2.data)['peers']), [ c3[0] ])
        self.assertEqual(sorted(utils.get_ips_from_pack(bencode.bdecode(respc3.data)['peers'])), sorted([ c1[0], c2[0] ]))

    def test_nonrepr_seeder_doesnt_get_seeders(self):
        """If a seeder requests peers, he should not get any seeders"""
        c1 = ('192.168.0.10', 'testrack1')
        c2 = ('192.168.0.11', 'testrack1')
        c3 = ('192.168.0.12', 'testrack1')
        c4 = ('192.168.0.13', 'testrack1')
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = testutils.get_ihash_from_filename(filename)
        filesz = testutils.get_size_from_filename(filename)
        testutils.post_torrent(self.client, filename)
        testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        testutils.add_client(self.app, ihash=ihash, ipaddress=c2[0], rackname=c2[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        testutils.add_client(self.app, ihash=ihash, ipaddress=c3[0], rackname=c3[1], event=None, mock_smdb=True, port=port, left=filesz) # Leecher
        testutils.add_client(self.app, ihash=ihash, ipaddress=c4[0], rackname=c4[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        respc1 = testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        respc2 = testutils.add_client(self.app, ihash=ihash, ipaddress=c2[0], rackname=c2[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        respc3 = testutils.add_client(self.app, ihash=ihash, ipaddress=c3[0], rackname=c3[1], event=None, mock_smdb=True, port=port, left=filesz) # Leecher
        respc4 = testutils.add_client(self.app, ihash=ihash, ipaddress=c4[0], rackname=c4[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        self.assertEqual(sorted(utils.get_ips_from_pack(bencode.bdecode(respc1.data)['peers'])), sorted([ c3[0] ]))
        self.assertEqual(sorted(utils.get_ips_from_pack(bencode.bdecode(respc2.data)['peers'])), sorted([ c3[0] ]))
        self.assertEqual(sorted(utils.get_ips_from_pack(bencode.bdecode(respc3.data)['peers'])), sorted([ c1[0], c2[0] , c4[0]]))
        self.assertEqual(sorted(utils.get_ips_from_pack(bencode.bdecode(respc4.data)['peers'])), sorted([ c3[0] ]))

    def deactivated_transfer_yields_empty_peerlist(self):
        c1 = ('192.168.0.10', 'testrack1')
        c2 = ('192.168.0.11', 'testrack2')
        c3 = ('192.168.0.12', 'testrack2')
        c4 = ('192.168.0.13', 'testrack3')
        port = 10004
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = testutils.get_ihash_from_filename(filename)
        filesz = testutils.get_size_from_filename(filename)
        testutils.post_torrent(self.client, filename)
        testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        testutils.add_client(self.app, ihash=ihash, ipaddress=c2[0], rackname=c2[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        testutils.add_client(self.app, ihash=ihash, ipaddress=c3[0], rackname=c3[1], event=None, mock_smdb=True, port=port, left=filesz) # Leecher
        testutils.add_client(self.app, ihash=ihash, ipaddress=c4[0], rackname=c4[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        testutils.delete_torrent(self.client, filename)
        resp = testutils.add_client(self.app, ihash=ihash, ipaddress=c1[0], rackname=c1[1], event=None, mock_smdb=True, port=port, left=0) # Seeder
        self.assert200(resp)
        self.assertEqual(sorted(utils.get_ips_from_pack(bencode.bdecode(resp.data)['peers'])), [])
