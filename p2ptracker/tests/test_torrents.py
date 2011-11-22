from __future__ import with_statement

from flaskext.testing import TestCase

from p2ptracker import create_app
from p2ptracker.tests.helpers import utils
import os
import logging
import redis
import shutil

__author__ = 'ramon'

REMOVE_LOG=False
SCRIPTDIR = os.path.dirname(__file__)
log = logging.getLogger('hyves.%s' % __name__)

class TestTorrents(TestCase):
    '''So test the torrent methods'''

    def create_app(self):
        return create_app()

    def setUp(self):
        r = redis.Redis(host=self.app.config['REDISHOST'], port=self.app.config['REDISPORT'])
        r.ping()
        r.flushdb()

    def tearDown(self):
        if os.path.exists('p2ptracker.log') and REMOVE_LOG:
            os.remove('p2ptracker.log')
        if os.path.exists(self.app.config['UPLOAD_PATH']):
            shutil.rmtree(self.app.config['UPLOAD_PATH'])
        r = redis.Redis(host=self.app.config['REDISHOST'], port=self.app.config['REDISPORT'])
        r.ping()
        r.flushdb()


    # Actual test methods
    def test_empty_torrents(self):
        '''Test that we get an empty dict if no torrent files have been registered'''
        url = "/torrents/"
        resp = self.client.get(url)
        self.assert200(resp)
        self.assertEquals(resp.json, dict())

    def test_post_torrent_falsefilename(self):
        resp = utils.post_torrentfile(self.client, 'ramon.txt', None)
        self.assert_status(resp, 501)

    def test_post_torrent_correctfilename(self):
        filename = '%s/test.torrent' % SCRIPTDIR
        try:
            file = open(filename, 'r')
            resp = utils.post_torrentfile(self.client, filename, file)
            self.assert200(resp)
        finally:
            file.close()

    def test_nonempty_torrents_after_post(self):
        '''test if we get a non-empty list back after we posted a torrent file'''
        try:
            filename = '%s/test.torrent' % SCRIPTDIR
            file = open(filename, 'r')
            utils.post_torrentfile(self.client, filename, file)
        finally:
            file.close()
            resp = self.client.get('torrents/')
            self.assert200(resp)
            assert(len(resp.json.keys()) > 0)
            self.assertEquals(resp.json.keys(), ['test.torrent'])

    def test_retrieve_torrentfile(self):
        try:
            filename = '%s/test.torrent' % SCRIPTDIR
            file = open(filename, 'r')
            utils.post_torrentfile(self.client, filename, file)
        finally:
            file.close()
        resp = utils.get_torrentfile(self.client, '%s/test.torrent' % SCRIPTDIR)
        self.assert200(resp)
        self.assertEquals(resp.data, open(filename, 'r').read())

    def test_delete_nonexistant_torrentfile(self):
        '''Make sure a torrentfile is actually deleted'''
        resp = utils.get_torrentfile(self.client, 'nonexistant.torrent')
        self.assert404(resp)

    def test_delete_existing_torrentfile(self):
        '''Delete a torrent file from the tracker'''
        try:
            filename = '%s/test.torrent' % SCRIPTDIR
            file = open(filename, 'r')
            resp = utils.post_torrentfile(self.client, filename, file)
            log.debug('resp on post: %s' % resp)
        finally:
            file.close()
        with self.app.test_client() as c:
            resp = c.delete('torrents/test.torrent')
            log.debug('delete resp: %s' % resp)
            log.debug('delet resp data: %s' % resp.data)
            self.assert200(resp)
        resp = utils.get_torrentfile(self.client, filename)
        self.assert404(resp)

