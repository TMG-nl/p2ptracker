__author__ = 'ramon'

from flaskext.testing import TestCase
import redis
from p2ptracker import create_app
from p2ptracker.tests.helpers import utils

import os
import logging
from mocker import Mocker

log = logging.getLogger('hyves.p2ptracker.test.test_transfers')
REMOVE_LOG = False
SCRIPTDIR = os.path.dirname(__file__)

class TestTransfers(TestCase):

    def create_app(self):
        return create_app()

    def setUp(self):
        self.mocker = Mocker()
        r = redis.Redis(host=self.app.config['REDISHOST'], port=self.app.config['REDISPORT'])
        r.ping()
        r.flushdb()

    def tearDown(self):
        if os.path.exists('p2ptracker.log') and REMOVE_LOG:
            os.remove('p2ptracker.log')
        r = redis.Redis(host=self.app.config['REDISHOST'], port=self.app.config['REDISPORT'])
        r.ping()
        r.flushdb()

    # Actual Test methods
    def test_transfers_with_no_data_and_params(self):
        '''Should return an empty dictionary'''
        resp = self.client.get('/transfers/')
        self.assert200(resp)
        self.assertEquals(resp.json, dict())

    def test_transfers_with_active_transfer(self):
        '''If a transfer is active, this will return a dict of hashes and their torrentfiles'''
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            ihash = utils.get_infohash_from_file(file)
            file.seek(0)
            utils.post_torrentfile(self.client, filename, file)
        except Exception, e:
            log.critical("Cannot open test torrent file")
            self.assertTrue(False, "%s" % e)
        finally:
            file.close()
        resp = self.client.get('/transfers/')
        self.assert200(resp)
        self.assertTrue(isinstance(resp.json, type(dict())))
        self.assertTrue(ihash in resp.json)

    def test_empty_stats(self):
        '''If we have no clients the stats should be empty ???'''
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        transfersize = utils.get_size_from_filename(filename)
        utils.post_torrent(self.client, filename)
        resp = self.client.get('/transfers/%s.json' % ihash)
        log.debug(resp)
        self.assert200(resp)
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 0)
        self.assertEquals(resp.json['global']['seeders'], 0)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '0.00%')

    def test_stats_with_a_seeder(self):
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            ihash = utils.get_infohash_from_file(file)
            transfersize = utils.get_size_from_torrentfile(file)
            file.seek(0)
            utils.post_torrentfile(self.client, filename, file)
        finally:
            file.close()
        try:
            ipaddress = '192.168.0.12'
            rackname = 'FA12'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=0)
        except Exception, e:
            raise e
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 1)
        self.assertEquals(resp.json['global']['seeders'], 1)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '100.00%')

    def test_stats_with_peer(self):
        '''Test a single peer'''
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            ihash = utils.get_infohash_from_file(file)
            transfersize = utils.get_size_from_torrentfile(file)
            file.seek(0)
            utils.post_torrentfile(self.client,filename, file)
        finally:
            file.close()
        try:
            ipaddress = '192.168.0.12'
            rackname = 'FA12'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize)
        except Exception, e:
            raise e
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 1)
        self.assertEquals(resp.json['global']['seeders'], 0)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '0.00%')

    def test_stats_with_seeder_and_peer(self):
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            ihash = utils.get_infohash_from_file(file)
            transfersize = utils.get_size_from_torrentfile(file)
            file.seek(0)
            utils.post_torrentfile(self.client, filename, file)
        finally:
            file.close()
        try:
            ipaddress = '192.168.0.12'
            rackname = 'FA12'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize)
        except Exception, e:
            raise e
        try:
            ipaddress = '192.168.0.13'
            rackname = 'FA13'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=0)
        except Exception, e:
            raise e
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 2)
        self.assertEquals(resp.json['global']['seeders'], 1)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '50.00%')

    def test_stats_progress(self):
        '''Test a single peer progress'''
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            ihash = utils.get_infohash_from_file(file)
            transfersize = utils.get_size_from_torrentfile(file)
            file.seek(0)
            utils.post_torrentfile(self.client, filename, file)
        finally:
            file.close()
        try:
            ipaddress = '192.168.0.12'
            rackname = 'FA12'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize, mock_smdb=True)
        except Exception, e:
            raise e
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 1)
        self.assertEquals(resp.json['global']['seeders'], 0)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '0.00%')
        try:
            ipaddress = '192.168.0.12'
            rackname = 'FA12'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=(transfersize/4*3), mock_smdb=False)
        except Exception, e:
            raise e
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 1)
        self.assertEquals(resp.json['global']['seeders'], 0)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '25.00%')

    def test_start_event_handling(self):
        '''Test a single peer progress'''
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        transfersize = utils.get_size_from_filename(filename)
        utils.post_torrent(self.client, filename)
        try:
            ipaddress = '192.168.0.12'
            rackname = 'FA12'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize, event='started', mock_smdb=True)
        except Exception, e:
            raise e
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 1)
        self.assertEquals(resp.json['global']['seeders'], 0)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '0.00%')
        self.assertTrue(resp.json['global']['first_start'] is not None)
        self.assertTrue(resp.json['global']['last_start'] is not None)
        self.assertTrue(resp.json['global']['first_complete'] is None)
        self.assertTrue(resp.json['global']['last_complete'] is None)
        self.assertEqual(resp.json['global']['first_start'], resp.json['global']['last_start'])
        utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize, event='started', mock_smdb=True)
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        self.assertNotEqual(resp.json['global']['first_start'], resp.json['global']['last_start'])


    def test_stopped_event_handling(self):
        '''Test a single peer progress'''
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            ihash = utils.get_infohash_from_file(file)
            transfersize = utils.get_size_from_torrentfile(file)
            file.seek(0)
            utils.post_torrentfile(self.client, filename, file)
        finally:
            file.close()
        try:
            ipaddress = '192.168.0.12'
            rackname = 'FA12'
            utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize, event='stopped', mock_smdb=True)
        except Exception, e:
            raise e
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 1)
        self.assertEquals(resp.json['global']['seeders'], 0)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '0.00%')
        self.assertTrue(resp.json['global']['first_start'] is  None)
        self.assertTrue(resp.json['global']['last_start'] is  None)
        self.assertTrue(resp.json['global']['first_complete'] is None)
        self.assertTrue(resp.json['global']['last_complete'] is None)

    def test_completed_event_handling(self):
        '''Test a single peer progress'''
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            ihash = utils.get_infohash_from_file(file)
            transfersize = utils.get_size_from_torrentfile(file)
            file.seek(0)
            utils.post_torrent(self.client, filename)
        finally:
            file.close()
        ipaddress = '192.168.0.12'
        rackname = 'FA12'
        utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize, event='completed', mock_smdb=True)
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertTrue('global' in resp.json)
        self.assertEquals(resp.json['global']['size'], str(transfersize))
        self.assertEquals(resp.json['global']['peers'], 1)
        self.assertEquals(resp.json['global']['seeders'], 0)
        self.assertEquals(resp.json['global']['active'], True)
        self.assertEquals(resp.json['global']['progress'], '0.00%')
        self.assertTrue(resp.json['global']['first_start'] is  None)
        self.assertTrue(resp.json['global']['last_start'] is  None)
        self.assertTrue(resp.json['global']['first_complete'] is not None)
        self.assertTrue(resp.json['global']['last_complete'] is not None)
        self.assertEqual(resp.json['global']['first_complete'], resp.json['global']['last_complete'])
        utils.add_client(self.app, ihash, ipaddress, rackname, left=transfersize, event='completed', mock_smdb=True)
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert200(resp)
        print resp.json
        self.assertNotEqual(resp.json['global']['first_complete'], resp.json['global']['last_complete'])

    def test_get_peers_for_transfer(self):
        '''This method tests the additional rest style interface to get at peers and seeders'''
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        utils.post_torrent(self.client, filename)
        utils.add_client(self.app, ihash, '192.168.0.11', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.12', port=10004, rackname='testrack1', left=0)
        resp = self.client.get('/transfers/peers/%s.json' % ihash)
        print resp.data
        print resp.json
        self.assert200(resp)
        self.assertTrue('peers' in resp.json)
        self.assertEqual(sorted(resp.json['peers']), ['192.168.0.11:10004', '192.168.0.12:10004'])

    def test_get_seeders_for_transfer(self):
        '''This method tests the additional rest style interface to get at peers and seeders'''
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        utils.post_torrent(self.client, filename)
        utils.add_client(self.app, ihash, '192.168.0.11', port=10004, rackname='testrack1', left=0)
        utils.add_client(self.app, ihash, '192.168.0.12', port=10004, rackname='testrack1', left=0)
        resp = self.client.get('/transfers/seeders/%s.json' % ihash)
        print resp.data
        print resp.json
        self.assert200(resp)
        self.assertTrue('seeders' in resp.json)
        self.assertEqual(sorted(resp.json['seeders']), ['192.168.0.11:10004', '192.168.0.12:10004'])

    def test_get_leechers_for_transfer(self):
        '''This method gets the remaining leechers'''
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        utils.post_torrent(self.client, filename)
        utils.add_client(self.app, ihash, '192.168.0.11', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.12', port=10004, rackname='testrack1', left=0)
        utils.add_client(self.app, ihash, '192.168.0.13', port=10004, rackname='testrack2', left=10000)
        resp = self.client.get('/transfers/leechers/%s.json' % ihash)
        print resp.data
        print resp.json
        self.assert200(resp)
        self.assertTrue('leechers' in resp.json)
        self.assertEqual(sorted(resp.json['leechers']), ['192.168.0.11:10004', '192.168.0.13:10004'])


    def test_get_repr_for_transfer(self):
        '''This method gets the all the reprs'''
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        utils.post_torrent(self.client, filename)
        utils.add_client(self.app, ihash, '192.168.0.11', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.12', port=10004, rackname='testrack1', left=0)
        utils.add_client(self.app, ihash, '192.168.0.13', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.14', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.15', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.16', port=10004, rackname='testrack2', left=10000)
        resp = self.client.get('/transfers/representants/%s.json' % ihash)
        print resp.data
        print resp.json
        self.assert200(resp)
        self.assertTrue('representants' in resp.json)
        self.assertEqual(sorted(resp.json['representants']),
            ['192.168.0.11:10004', '192.168.0.12:10004', '192.168.0.14:10004', '192.168.0.15:10004'])

    def test_get_racks_for_transfer(self):
        '''This method gets a list of racks involved in the transfer'''
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        utils.post_torrent(self.client, filename)
        utils.add_client(self.app, ihash, '192.168.0.11', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.12', port=10004, rackname='testrack1', left=0)
        utils.add_client(self.app, ihash, '192.168.0.13', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.14', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.15', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.16', port=10004, rackname='testrack2', left=10000)
        resp = self.client.get('/transfers/racks/%s.json' % ihash)
        print resp.data
        print resp.json
        self.assert200(resp)
        self.assertTrue('racks' in resp.json)
        self.assertEquals(sorted(resp.json['racks']), ['testrack1', 'testrack2'])

    def test_remove_transfer(self):
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        utils.post_torrent(self.client, filename)
        utils.add_client(self.app, ihash, '192.168.0.11', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.12', port=10004, rackname='testrack1', left=0)
        utils.add_client(self.app, ihash, '192.168.0.13', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.14', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.15', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.16', port=10004, rackname='testrack2', left=10000)
        resp = self.client.get('/transfers/racks/%s.json' % ihash)
        self.assert200(resp)
        self.assertTrue('racks' in resp.json)
        self.assertEquals(sorted(resp.json['racks']), ['testrack1', 'testrack2'])
        resp = self.client.delete('/transfers/%s.json' % ihash)
        self.assert200(resp)
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert404(resp)
        resp = self.client.get('/transfers/')
        self.assert200(resp)
        self.assertEqual(resp.json, dict())
        resp = self.client.get('/torrents/')
        self.assert200(resp)
        self.assertEqual(resp.json, dict())
        r = redis.Redis(host=self.app.config['REDISHOST'], port=self.app.config['REDISPORT'])
        keylist = list(r.keys('*'))
        for key in keylist:
            self.assertTrue(ihash not in key.split(':'))

    def test_remove_all_transfers(self):
        filename = '%s/test.torrent' % SCRIPTDIR
        ihash = utils.get_ihash_from_filename(filename)
        utils.post_torrent(self.client, filename)
        utils.add_client(self.app, ihash, '192.168.0.11', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.12', port=10004, rackname='testrack1', left=0)
        utils.add_client(self.app, ihash, '192.168.0.13', port=10004, rackname='testrack1', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.14', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.15', port=10004, rackname='testrack2', left=10000)
        utils.add_client(self.app, ihash, '192.168.0.16', port=10004, rackname='testrack2', left=10000)
        resp = self.client.get('/transfers/racks/%s.json' % ihash)
        self.assert200(resp)
        self.assertTrue('racks' in resp.json)
        self.assertEquals(sorted(resp.json['racks']), ['testrack1', 'testrack2'])
        resp = self.client.delete('/transfers/')
        self.assert200(resp)
        resp = self.client.get('/transfers/%s.json' % ihash)
        self.assert404(resp)
        resp = self.client.get('/transfers/')
        self.assert200(resp)
        self.assertEqual(resp.json, dict())
        resp = self.client.get('/torrents/')
        self.assert200(resp)
        self.assertEqual(resp.json, dict())
        r = redis.Redis(host=self.app.config['REDISHOST'], port=self.app.config['REDISPORT'])
        self.assertTrue(list(r.keys('*')) == [])

