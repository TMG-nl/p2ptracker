__author__ = 'ramon'

from flask import Module, request, abort, make_response, Response, jsonify, g, send_from_directory, current_app
from werkzeug import secure_filename
from p2ptracker import bencode
import logging
import hashlib
import os
from datetime import datetime

torrents = Module(__name__, url_prefix='/torrents')

log = logging.getLogger('hyves.p2ptracker.torrent')

@torrents.route('/<filename>.<ext>', methods=['DELETE'])
def delete(filename, ext):
    torrentfile = "%s.%s" % (filename, ext)
    if torrentfile not in get_all_torrents():
        log.debug('torrentfile: %s not in %s' % (torrentfile, get_all_torrents()))
        return abort(404, 'no such torrent')
    if os.path.exists(os.path.join(current_app.config['UPLOAD_PATH'], torrentfile)):
        log.debug('Deleting file: %s' % torrentfile)
        os.remove(os.path.join(current_app.config['UPLOAD_PATH'], torrentfile))
        return make_response(Response('', status=200))
    return abort(500, 'something borked horribly')

@torrents.route('/<filename>.<ext>', methods=['POST'])
def post(filename, ext):
    """
    Pull filename for torrent and actually uploaded torrentfile from request and register in redis
    We add the torrent file to the all torrents set in redis and
    register the torrentfile name along with the associated hash
    """
    log.debug("Entering post method")
    assert isinstance(filename, basestring)
    assert isinstance(ext, basestring)
    torrentfile = filename + '.' + ext
    log.debug("torrentfile: %s" % torrentfile)
    if ext != 'torrent':
        return abort(501, "Invalid filename specified, needs to end in .torrent")
    log.debug('request: %s' % request)
    log.debug("%s" % request.files)
    if len(request.files.keys()) > 1:
        abort(400, 'Bad Request, multiple files uploaded')
    save_torrent(torrentfile, request.files.values()[0])
    data = request.files.values()[0]
    data.seek(0)
    torrentdata = bencode.bdecode(data.read())
    ihash = get_infohash_from_torrent(torrentdata)
    name = get_name_from_torrent(torrentdata)
    length = get_length_from_torrent(torrentdata)
    activate(ihash, name, length )
    log.debug("file: %s" % torrentdata.keys())
    return make_response(Response('', status=200))

@torrents.route('/', methods=['GET'])
@torrents.route('/<filename>.<ext>', methods=['GET'])
def get(filename=None, ext=None):
    if not filename and not ext:
        return jsonify(get_all_torrents())
    torrentfile = "%s.%s" % (filename, ext)
    if torrentfile not in get_all_torrents():
        return abort(404, 'torrentfile not found')
    return send_from_directory(current_app.config['UPLOAD_PATH'],
                               torrentfile, as_attachment=True)

def get_infohash_from_torrent(data):
    """Return the sha1 hash for the torrent"""
    return hashlib.sha1(bencode.bencode(data['info'])).hexdigest()

def get_length_from_torrent(data):
    """Return torrent length in bytes"""
    length = 0
    if 'files' in data['info']:
        length = sum(file['length'] for file in data['info']['files'])
    else:
        length += data['info']['length']
    return length

def get_name_from_torrent(data):
    return data['info']['name']

def save_torrent(torrentname, file):
    assert os.path.exists(current_app.config['UPLOAD_PATH'])
    filename = secure_filename(torrentname)
    log.debug('filenames: %s, %s' % (file.filename, filename))
    if os.path.basename(file.filename) != torrentname:
        abort(500, '''filenames don't match''')
    g.redis.sadd('torrents', torrentname)
    file.save(os.path.join(current_app.config['UPLOAD_PATH'], filename))
    log.info('saved file as %s' % os.path.join(current_app.config['UPLOAD_PATH'], filename))
    file.seek(0)
    ihash = get_infohash_from_torrent(bencode.bdecode(file.read()))
    g.redis.set(torrentname, ihash)

def get_torrent(torrentname):
    return g.redis.get(torrentname)

def get_all_torrents():
    torrentfiles = list(g.redis.smembers('torrents'))
    if torrentfiles:
        return dict(zip(torrentfiles, list(g.redis.mget(torrentfiles))))
    return dict()

def activate(ihash, name, length):
    if not g.redis.sismember('transfers', ihash):
        log.warning("Transfer: %s hasn't started yet" % ihash)
        g.redis.sadd('transfers', ihash)
    now = "%s" % datetime.now()
    g.redis.sadd('active_transfers', ihash)
    args = {
        '%s:registered' % ihash: now,
        '%s:name' % ihash: name,
        '%s:length' % ihash: length
    }
    g.redis.mset(args )

