from __future__ import with_statement

from p2ptracker import bencode
import hashlib
import binascii
import urllib
import logging
import os
import redis
import socket
import shutil
from mocker import Mocker

__author__ = 'ramon'
log = logging.getLogger("hyves.%s" % __name__)

def write_redis_config(port=6379, host='127.0.0.1', dbfilename="redis.db", redisdir='/tmp/redis-test'):
    """Write a reasonable redis config file for use in testing"""
    if not os.path.exists(redisdir):
        os.makedirs(redisdir)
    params = dict(port=port, host=host, dbfilename=dbfilename,redisdir=redisdir)
    params['pidfile'] = "%s/pid" % redisdir
    params['logfile'] = "%s/redis.log" % redisdir
    params['host'] = socket.gethostbyname(params['host'])
    log.debug(params)
    config = """
    daemonize yes\n
    pidfile %(pidfile)s\n
    port %(port)s\n
    bind %(host)s\n
    timeout 30\n
    loglevel notice\n
    logfile %(logfile)s\n
    databases 16\n
    save 900 1\n\n
    save 300 10\n
    save 60 10000\n
    rdbcompression yes\n
    dbfilename %(dbfilename)s\n
    dir %(redisdir)s\n
    """ % params
    filename = os.path.join(os.path.dirname(__file__), 'redis-test.conf')
    file = open(filename, 'w')
    file.write(config)
    file.close()
    return filename


def start_redis_server(**kwords):
    '''Start a local instance of the redis server with data in tmp'''
    REDISCONF=write_redis_config(**kwords)
    try:
        REDISBIN=os.popen("source /etc/profile; which redis-server2 2>/dev/null").read().strip()
        if not REDISBIN:
            REDISBIN=os.popen("source /etc/profile; which redis-server").read().strip()
        log.debug("Found redis binary: %s" % REDISBIN)
    except:
        log.warning("Found no redis server, cannot proceed")
        raise
    try:
        os.system("%s %s" % (REDISBIN, REDISCONF))
    except:
        log.warning("Failed to start the redis server")
        raise

def stop_redis_server(port=6379, host='127.0.0.1', dbfilename="redis.db", redisdir='/tmp/redis-test'):
    r = redis.Redis(host, port)
    r.flushdb()
    r.shutdown()
    if os.path.exists(os.path.join(os.path.dirname(__file__), 'redis-test.conf')):
        os.remove(os.path.join(os.path.dirname(__file__), 'redis-test.conf'))
    if os.path.exists(redisdir):
        shutil.rmtree(redisdir)


def get_infohash_from_file(file):
    '''Return a string hash value for a torrentfile, raise exception otherwise'''
    file.seek(0)
    data = bencode.bdecode(file.read())
    return hashlib.sha1(bencode.bencode(data['info'])).hexdigest()

def get_size_from_torrentfile(file):
    '''Return an integer describing the size ofthe torrent payload'''
    file.seek(0)
    data = bencode.bdecode(file.read())
    length = 0
    if 'files' in data['info']:
        for file in data['info']['files']:
            length += file['length']
    else:
        length += data['info']['length']
    return length

def get_ihash_from_filename(filename):
    try:
        file = open(filename, 'r')
        return get_infohash_from_file(file)
    finally:
        file.close()

def get_size_from_filename(filename):
    try:
        file = open(filename, 'r')
        return get_size_from_torrentfile(file)
    finally:
        file.close()


def urlquote_ihash(ihash):
    hex_bin = binascii.unhexlify(ihash)
    return urllib.quote(hex_bin)


def mock_smdb_get_rack(ipaddress, rackname):
    mocker = Mocker()
    mocked_get_rack = mocker.replace('p2ptracker.smdbapi.get_rack')
    mocked_get_rack(ipaddress)
    mocker.result(rackname)
    mocker.replay()

def add_client(app, ihash, ipaddress, rackname, left,
               event=None, peer_id="test_client", port=10004,
               compact=1, uploaded=0, downloaded=0, key='test_key', mock_smdb=True):
    '''Call app with a suitable announce url to add a seeder'''
    #
    #'''/announce/'''
    #'''?info_hash=%13L%B2%81%DDT%02%1B%BF%D1l%B9%C6%25%1E%CD-g%DC%BF'''
    #'''&peer_id=-lt0C60-f%F2%3Ef%EC%E8%C0%21%EF%FFzM'''
    #'''&key=359a335e'''
    #'''&ip=10.2.5.18'''
    #'''&compact=1'''
    #'''&port=10004'''
    #'''&uploaded=1317224448'''
    #'''&downloaded=1073741824'''
    #'''&left=0'''
    if mock_smdb:
        mock_smdb_get_rack(ipaddress, rackname)
    params = dict()
    url = '/announce/?info_hash=%(ihash)s'
    url += '&peer_id=%(peer_id)s&key=%(key)s'
    url += '&compact=%(compact)s&ip=%(ipaddress)s&port=%(port)s&uploaded=%(uploaded)s'
    url += '&downloaded=%(downloaded)s&left=%(left)s'
    if event:
        url += '&event=%(event)s'
        params['event'] = event
    params.update({'ihash':urlquote_ihash(ihash), 'ipaddress':ipaddress, 'left':left, 'peer_id':peer_id,
                      'port':port, 'key':key, 'compact':compact, 'uploaded':uploaded,
                      'downloaded':downloaded})
    with app.test_client() as c:
        return c.get(url % params)

def post_torrent(client, filename):
    try:
        file = open(filename, 'r')
        return client.post('torrents/%s' % os.path.basename(filename), data={
            filename: [file] })
    finally:
        file.close()

def delete_torrent(client, filename):
    try:
        file = open(filename, 'r')
        return client.delete('torrents/%s' % os.path.basename(filename), data={
            filename: [file] })
    finally:
        file.close()

def get_torrentfile(client, filename):
    return client.get('torrents/%s' % os.path.basename(filename))

def post_torrentfile(client, filename, file):
    return client.post('torrents/%s' % os.path.basename(filename), data={
        filename: [file] })

