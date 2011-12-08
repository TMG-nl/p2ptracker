"""
https://github.com/hyves-org/p2ptracker
Copyright (c) 2011, Ramon van Alteren
MIT license: http://www.opensource.org/licenses/MIT

This module implements the rest methods possible on a transfer resource
"""

import logging
import hashlib
from p2ptracker import bencode, utils
from flask import make_response, Response, jsonify, abort, request, Module, g
from datetime import datetime

transfers = Module(__name__, url_prefix='/transfers')

log = logging.getLogger("hyves.p2ptracker.transfers")

@transfers.route('/peers/<info_hash>.<ext>', methods=['GET'])
def get_peers(info_hash, ext):
    peerlist = list(g.redis.smembers('%s:peers:N' % info_hash))
    return jsonify(peers=peerlist)

@transfers.route('/seeders/<info_hash>.<ext>', methods=['GET'])
def get_seeders(info_hash, ext):
    seederlist = list(g.redis.smembers('%s:peers:S' % info_hash))
    return jsonify(seeders=seederlist)

@transfers.route('/representants/<info_hash>.<ext>', methods=['GET'])
def get_representants(info_hash, ext):
    representantslist = list(g.redis.smembers('%s:peers:R' % info_hash))
    return jsonify(representants=representantslist)

@transfers.route('/leechers/<info_hash>.<ext>', methods=['GET'])
def get_leechers(info_hash, ext):
    leecherlist = list(g.redis.sdiff(['%s:peers:N' % info_hash, '%s:peers:S' % info_hash ]))
    return jsonify(leechers=leecherlist)

@transfers.route('/racks/<info_hash>.<ext>', methods=['GET'])
def get_racks(info_hash, ext):
    rackslist = list(g.redis.smembers('%s:racks' % info_hash))
    return jsonify(racks=rackslist)

@transfers.route('/', methods=['DELETE'])
@transfers.route('/<ihash>.<ext>', methods=['DELETE'])
def delete(ihash=None, ext='json'):
    """remove a transfer from active use"""
    log.debug("infohash: %s" % ihash)
    if ext not in ['json', 'torrent']:
        log.error('only json type are supported atm')
        ext = 'json'
    if not ihash:
        flush_all_transfers()
        return make_response(Response('Deleted all transfers', status=200))
    deactivate(ihash)
    return make_response(Response('deleting transfer: %s' % ihash, status=200))

@transfers.route('/', methods=['GET'])
@transfers.route('/<ihash>.<ext>', methods=['GET'])
def get(ihash=None, ext='json'):
    log.debug("infohash: %s" % ihash)
    if ext not in ['json', 'torrent']:
        log.error('only json type are supported atm')
        ext = 'json'
    if not ihash:
        transfers = get_all_transfers()
        log.debug(transfers)
        return jsonify(transfers)
    return jsonify(get_stats(ihash, request.args))

def get_infohash(data):
    """Return the sha1 hash for the torrent"""
    return hashlib.sha1(bencode.bencode(data['info'])).hexdigest()

def get_length(data):
    """Return torrent length in bytes"""
    length = 0
    if 'files' in data['info']:
        for file in data['info']['files']:
            length += file['length']
    else:
        length += data['info']['length']
    return length

def get_name(data):
    return data['info']['name']

def get_stats(ihash,args):
    """Return a dict with the stats"""
    if not ihash in get_all_transfers():
        abort(404, 'No such info_hash found')
    if args.get('racks'):
        return {
            "global": get_global_stats(ihash),
            "racks": get_rack_stats(ihash)
        }
    return {
        "global": get_global_stats(ihash)
    }

def get_global_stats(ihash):
    peers = list(p.split(':')[0] for p in get_peers_redis(ihash))
    return {
        "active": utils.is_active(ihash),
        "peers": get_peer_count(ihash),
        "started": get_transfer_start(ihash),
        "seeders": get_seeder_count(ihash),
        "leechers": get_leecher_count(ihash),
        "first_start": get_first_started(ihash),
        "last_start": get_last_started(ihash),
        "complete": transfer_done(ihash),
        "first_complete": get_first_completed(ihash),
        "last_complete": get_last_completed(ihash),
        "size": get_size(ihash),
        "progress": estimate_progress(ihash, peers),
    }

def get_rack_stats(ihash):
    """
    Get stats about the different racks
    returns a dict {
        "rackname": {
            "R": <count of reprs>,
            "N": <count of peers>,
            "S": <count of seeders>,
            "progress": percentage
        }
    }
    """
    stats = {}
    racks = list(get_racks())
    log.debug("Processing stats for racks: %s" % racks)
    for rack in racks:
        log.debug("getting stats for rack: %s" % rack)
        stats[rack] = get_rack_peer_stats(ihash, rack)
        log.debug("Stats for rack: %s" % stats[rack])
    return stats

def get_rack_peer_stats(ihash, rack):
    """
    Get stats for all peers in a rack
    returns {
        "R": <count of reprs>,
        "N": <count of peers>,
        "S": <count of seeders>,
        "progress": percentage
    }
    """
    stats = {
        "N": get_peercount_for_rack(ihash, rack),
        "R": get_reprcount_for_rack(ihash, rack),
        "S": get_seedercount_for_rack(ihash, rack)
    }
    peers = get_peers_for_rack(ihash, rack)
    stats["progress"] = estimate_progress(ihash, peers)
    return stats

def estimate_progress(ihash, peers):
    """Estimate a percentage done based on client stats"""
    progress = count = 0
    log.debug("peers: %s" % peers)
    size = float(get_size(ihash))
    if not size:
        return "Unknown"
    stats = get_clientstats(ihash)
#    log.debug("%s" % stats)
    for peer in peers:
        progress += float(stats["%s:peer:%s:left" % (ihash, peer)])
    try:
        percentage = 100 - (( progress / float(len(peers)) ) / size * 100)
    except ZeroDivisionError:
        if transfer_complete_for_peers(ihash, peers) and count == 0 and len(peers) > 0:
            percentage = 100.00
        else:
            percentage = 0.00
    log.debug("progress: %s, perc: %s, count: %s, peers: %s" % ( progress, percentage, count, peers))
    return "%0.2f%%" % percentage

def transfer_complete_for_peers(ihash, peers):
    """Return True if all peers are done"""
    log.debug("Entering complete_for_peers: %s, %s" % (ihash, peers))
    for peer in peers:
        if not peer_is_seeder(ihash, peer):
            return False
    return True

def transfer_done(ihash):
    """Return True if transfer is done"""
    # When is a transfer done ?
    # All peers == seeders  and hash.last_completed has some data.
    # Seeders that have never downloaded will never report a completed event
    # hence this should be fairly accurate metric except in restarts
    return get_peer_count(ihash) == get_seeder_count(ihash) \
        and has_completed_event(ihash)

def get_all_transfers():
    """This returns a dict of all ihashes and their associated torrent file"""
    torrentfiles = list(g.redis.smembers('torrents'))
    log.debug('torrentfiles=%s' % torrentfiles)
    if torrentfiles:
        return dict(zip(list(g.redis.mget(torrentfiles)), torrentfiles))
    return dict()

def deactivate(ihash):
    """Deactivate an active transfer"""
    if not g.redis.sismember('active_transfers', ihash):
        raise ValueError("Transfer: %s wasn't activated yet" % ihash)
    g.redis.srem('active_transfers', ihash)
    g.redis.srem('transfers', ihash)
    torrentdict = get_all_transfers()
    log.debug('torrentdict = %s' % torrentdict)
    if ihash in torrentdict:
        g.redis.delete(torrentdict[ihash])
        g.redis.srem("torrents", torrentdict[ihash])
    keys = g.redis.keys('%s*' % ihash)
    now = "%s" % datetime.now()
    p = g.redis.pipeline()
    for k in keys:
        p.delete(k)
    p.execute()

def flush_all_transfers():
    """Completely clear all information from redis"""
    return g.redis.flushall()

def get_completed_transfers():
    """Return a list of hashes with all transfers that are complete"""
    return [ transfer for transfer in get_all_transfers() if get_peer_count(transfer) == get_seeder_count(transfer) and has_completed_event(transfer) ]


def get_inprogress_transfers():
    return [ transfer for transfer in get_all_transfers() if get_peer_count(transfer) > get_seeder_count(transfer) ]


def get_peer_count(ihash):
    """Return count of all participating peers we've seen"""
    return g.redis.scard("%s:peers:N" % ihash)


def get_peercount_for_rack(ihash, rack):
    return g.redis.scard("%s:rack:%s:N" % (ihash, rack))


def get_reprcount_for_rack(ihash, rack):
    return g.redis.scard("%s:rack:%s:R" % (ihash, rack))


def get_seedercount_for_rack(ihash, rack):
    return g.redis.scard("%s:rack:%s:S" % (ihash, rack))


def get_transfer_start(ihash):
    """Return datetime string when the transfer started"""
    return g.redis.get("%s:registered" % ihash)


def get_last_completed(ihash):
    """return a datetime string with the last completed event reported"""
    return g.redis.get("%s:last_completed" % ihash)


def get_first_completed(ihash):
    """return a datetime string with the last completed event reported"""
    return g.redis.get("%s:first_completed" % ihash)


def get_first_started(ihash):
    return g.redis.get("%s:first_started" % ihash)


def get_last_started(ihash):
    return g.redis.get("%s:last_started" % ihash)


def get_seeder_count(ihash):
    """Return amount of seeders for this hash"""
    if g.redis.exists("%s:peers:S" % ihash):
        return g.redis.scard("%s:peers:S" % ihash)
    return 0


def get_leecher_count(ihash):
    """Return amount of leechers for this hash"""
    if g.redis.exists("%s:peers:L" % ihash):
        return g.redis.scard("%s:peers:L" % ihash)
    return 0

def get_size(ihash):
    """Get size in bytes for the torrent transfer if it is known"""
    if g.redis.exists("%s:length" % ihash):
        return g.redis.get("%s:length" % ihash)
    return 0
def get_clientstats(ihash):
    """Get a dictionary of stat data for all clients involved in the transfer"""
    keys = list(g.redis.keys("%s:peer:*" % ihash))
    if not len(keys):
        return {}
    values = g.redis.mget(keys)
    return dict(zip(keys, values))

def get_peers_redis(ihash):
    """Get all peers"""
    return g.redis.smembers("%s:peers:N" % ihash)


def get_peers_for_rack(ihash, rack):

    return list(p.split(':')[0] for p in g.redis.smembers("%s:rack:%s:N" % (ihash, rack)))


def peer_is_seeder(ihash, peer):
    return g.redis.get("%s:peer:%s:seeder" % (ihash, peer)) == "True"


def has_completed_event(ihash):
    return  g.redis.exists("%s:last_completed" % ihash)
