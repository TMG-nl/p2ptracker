"""
https://github.com/hyves-org/p2ptracker
Copyright (c) 2011, Ramon van Alteren
MIT license: http://www.opensource.org/licenses/MIT

Module to handle announce url for the tracker
"""

from p2ptracker import smdbapi, utils, bencode
from flask import request, current_app, Module, g
import logging
import socket
import random
from datetime import datetime

log = logging.getLogger("hyves.p2ptracker.announce")

announce = Module(__name__, url_prefix='/announce')

@announce.route('/', methods=["GET"])
def rest_announce():
    try:
        log.debug("Enter announce")
        ACTIVE_INTERVAL = current_app.config['ACTIVE_INTERVAL']
        PASSIVE_INTERVAL = current_app.config['PASSIVE_INTERVAL']
        ihash = utils.get_hash_hex(request.args.get('info_hash'))
        log.debug("ihash: %s" % ihash)
        if request.args.get('ip'):
            ipaddress = request.args.get('ip')
        else:
            ipaddress = request.remote_addr
        port = request.args.get('port')
        thispeer = "%s:%s" % (ipaddress, port)
        log.debug("peerpair: %s" % thispeer)
        seeder = int(request.args.get('left')) == 0
        active = utils.is_active(ihash)
        if active:
            interval = ACTIVE_INTERVAL
            if peer_first_announce(ihash, thispeer):
                store_peer_data(request.args, ihash, thispeer)
            else:
                update_peer_data(request.args, ihash, thispeer)
            warning = ""
        else:
            interval = PASSIVE_INTERVAL
            warning = "No active transfer for that info_hash: %s" % ihash
        peers = get_peers_for_peer(
                ihash,
                thispeer,
                seeder,
                active
            )
        if thispeer in peers:
            peers.remove(thispeer)
        log.debug("Will send thispeer: %s these peers: %s" % (thispeer, peers))
        if request.args.get('compact') == '1':
            peerlist = ""
            for peer in peers:
                peerlist += convert_peerpair_to_pack(peer)
        else:
            peerlist = []
            for peer in peers:
                peerlist.append(convert_peerpair_to_rec(ihash, peer))
        response = { "interval": interval, "warning": warning, "peers": peerlist }
        log.debug("resp: %s " % response)
        return bencode.bencode(response)
    except Exception, e:
        log.critical("Caught unhandled exception in announce")
        log.exception(e)
        raise e

def get_peers_for_peer(ihash, peer, seeder, active):
    """Get the peers for a peer, according to the rules"""
    peerlist = [] # Always return something
    if not active:
        add_transfer(ihash)
        log.debug("Transfer: %s is inactive")
        peerlist = []
        return peerlist
    log.debug("transfer: %s is active")
    rack = get_rack_for_peer(ihash, peer)
    if not rack:
        rack = get_rack_for_peer(ihash, peer)
    if promote_to_rack_repr(ihash, rack, peer) or is_rack_repr(ihash, rack, peer):
        log.info("I'm a rack repr: %s" % peer)
        peerlist = get_outside_peers(ihash, rack, seeder)
    else:
        log.info("I'm a normal peer: %s" % peer)
        peerlist = get_inside_peers(ihash, rack)
    if seeder:
        return filter_seeders(ihash, peerlist)
    else:
        return peerlist

def filter_seeders(ihash, peerlist):
    """Filter all known seeders from a list of peers"""
    seeders = g.redis.smembers("%s:peers:S" % ihash)
    filtered = list(set(peerlist).difference(set(seeders)))
    log.debug(filtered)
    return filtered

def get_inside_peers(ihash, rack):
    return get_rack_peers(ihash, rack)

def get_outside_peers(ihash, rack, seeder):
    max_peers = int(current_app.config['MAXPEERS'])
    peerlist = []
    peerlist.extend(get_rack_peers(ihash, rack))
    if not seeder:
        peerlist.extend(get_seeders(ihash))
    if max_peers - len(peerlist) > 0:
        peerlist.extend(get_representants(ihash, (max_peers-len(peerlist))))
    return utils.unique(peerlist)

def promote_to_rack_repr(ihash, rack, peer):
    """Find out if we can promote this peer to a rack repr"""
    add_to_rack(rack, peer)
    if is_rack_repr(ihash, rack, peer):
        log.info("%s is already a rack repr" % peer)
        return False
    if rack_repr_slots_filled(ihash, rack, peer):
        log.info("No more slots left for reprs in this rack: %s" % rack)
        set_rack_peer(ihash, rack, peer)
        return False
    set_rack_repr(ihash, rack, peer)
    log.info("Promoted %s to repr for rack %s" % (peer, rack))
    return True

def convert_peerpair_to_rec(ihash, pairstring):
    """Converts a ipaddress:port string into a dict rec"""
    ipaddress, port = pairstring.split(':')
    peer_id = get_peerid(ihash, ipaddress)
    peer_dict = { "ip":ipaddress, "port": int(port), "peer id":peer_id }
    return peer_dict

def convert_peerpair_to_pack(pairstring):
    ipaddress, port = pairstring.split(':')
    packed_port = "".join(reversed(utils.to_bytes(int(port)))) or chr(0)
    packed_ip = socket.inet_aton(ipaddress)
    return packed_ip + packed_port

def store_peer_data(args, ihash, peer):
    """Stores peer data in redis for retrieval"""
    ipaddress, port = peer.split(':')
    prefix = "%s:peer:%s:" % (ihash, ipaddress)
    now = "%s" % datetime.now()
    p = g.redis.pipeline()
    argsnx = {
        prefix + 'peer_id': args['peer_id'],
        prefix + 'port': port,
        prefix + 'key': args['key'],
        prefix + 'compact': args['compact'],
        }
    rargs = {
        prefix + 'downloaded': args['downloaded'],
        prefix + 'uploaded': args['uploaded'],
        prefix + 'left': args['left'],
        }
    if 'event' in args:
        event = args['event']
        rargs.update({
            prefix + 'last_event': event,
            prefix + 'event:%s' % event: now,
            '%s:last_%s' % (ihash, event): now,
            })
        argsnx.update({
            '%s:first_%s' % (ihash, event): now,
            })
    if args['left'] == 0:
        rargs[prefix + 'seeder'] = '%s' % args['left']
    p.mset(rargs)
    p.msetnx(argsnx)
    if not g.redis.exists(prefix + 'rack'):
        log.info('no rack found in redis')
        rack = smdbapi.get_rack(ipaddress)
        p.set(prefix + 'rack', rack)
        p.sadd('%s:racks' % ihash, rack)
        p.sadd('racks', rack)
    else:
        rack = g.redis.get(prefix + 'rack')
    p.sadd('rack:%s' % rack, ipaddress)
    p.sadd('racks', rack)
    if not g.redis.exists(prefix + 'hostname'):
        p.set(prefix + 'hostname', utils.resolve_ipaddress(ipaddress))
    log.debug("pipeline filled")
    p.execute()
    log.debug("Executed pipeline")
    # Allways add to hash:peers:N
    g.redis.sadd("%s:peers:N" % ihash, peer)
    g.redis.sadd("%s:rack:%s:N" % (ihash, rack), peer)
    if int(args['left']) == 0:
        update_seeder_status(ihash, rack, peer)

def update_peer_data(args, ihash, peer):
    """
    We already stored the normal data, only updating changed data
    data that can change:
     event
     downloaded
     uploaded
     left
    If the peer turned into a seeder we need to add him to the relevant set as well
    """
    ipaddress, port = peer.split(':')
    log.debug('ipaddress:%s, port:%s' % (ipaddress, port))
    prefix = '%s:peer:%s' % (ihash, ipaddress)
    now = datetime.now()
    rack = get_rack_for_peer(ihash, "%s:%s" % (ipaddress, args.get('port')))
    rargs = dict()
    p = g.redis.pipeline()
    rargs.update({
        prefix + 'downloaded': args['downloaded'],
        prefix + 'uploaded': args['uploaded'],
        prefix + 'left': args['left'],
        })
    if 'event' in args:
        event = args['event']
        rargs.update({
            prefix + 'last_event': event,
            prefix + 'event:%s' % event: now,
            '%s:last_%s' % (ihash, event): now,
            })
        argsnx = {
            '%s:first_%s' % (ihash, event): now,
            }
        p.msetnx(argsnx)
    rargs[prefix + 'seeder'] = '%s' % args['left'] == '0',
    p.mset(rargs)
    log.debug("pipeline filled")
    p.execute()
    log.debug("Executed pipeline")
    if args.get('left') == '0':
        update_seeder_status(ihash, rack, peer)

def update_seeder_status(ihash, rack, peer):
    g.redis.sadd( "%s:peers:S" % ihash, peer)
    g.redis.sadd( "%s:rack:%s:S" % (ihash, rack), peer)

def peer_first_announce(ihash, peer):
    """Are we seeing this peer for the first time or have we seen it before"""
    return not g.redis.exists('%s:peer:%s' % (ihash, peer.split(':')[0]))

def get_rack_for_peer(ihash, peer):
    """return rack name for peer"""
    return g.redis.get("%s:peer:%s:rack" % (ihash, peer.split(':')[0]))

def get_seeders(ihash):
    return list(g.redis.smembers("%s:peers:S" % ihash))

def get_representants(ihash, count=50):
    all_repr = list(g.redis.smembers("%s:peers:R" % ihash))
    log.info("Found %s representants with a max requested of %s" % (len(all_repr), count))
    if len(all_repr) <= count:
        log.debug("returning reprs: %s" % all_repr)
        return all_repr
    try:
        reprs = random.sample(all_repr, count)
    except ValueError, e:
        log.critical('sample larger than population')
        log.critical('population: %s, sample:%s' % (len(all_repr), count))
        raise e
    log.debug("returning reprs: %s" % reprs)
    return reprs

def add_to_rack(rack, peer):
    """Add a peer to a rack"""
    if not g.redis.sismember('racks', rack):
        add_rack(rack)
    g.redis.sadd('rack:%s' % rack, peer.split(':')[0])

def get_rack_peers(ihash, rack):
    """Return all peers in a rack"""
    return list(g.redis.smembers("%s:rack:%s:N" % (ihash, rack)))

def add_transfer(ihash):
    """Add a transfer"""
    g.redis.sadd('transfers', ihash)

def is_rack_repr(ihash, rack, peer):
    """Is this peer already a rack repr?"""
    return g.redis.sismember("%s:rack:%s:R" % (ihash, rack), peer)

def set_rack_peer(ihash, rack, peer):
#    key = "%s:rack:%s:N" % (ihash, rack)
    g.redis.sadd("%s:rack:%s:N" % (ihash, rack), peer)

def rack_repr_slots_filled(ihash, rack, peer):
    """Returns False if there are slots left for a rack repr"""
    key = "%s:rack:%s:R" % (ihash, rack)
    enough_reprs = (g.redis.scard(key) >= current_app.config['MAX_REPR_RACK'])
    return enough_reprs

def set_rack_repr(ihash, rack, peer):
    """Make peer the repr for the rack"""
    key = "%s:rack:%s:" % (ihash, rack )
    assert g.redis.scard(key) < current_app.config['MAX_REPR_RACK']
    p = g.redis.pipeline()
    p.sadd(key + 'R', peer)
    p.sadd(key + 'N', peer)
    p.sadd("%s:peers:R" % ihash, peer)
    p.sadd("%s:peers:N" % ihash, peer)
    p.execute()

def get_peerid(ihash, ipaddress):
    return g.redis.get("%s:peer:%s:peer_id" % (ihash, ipaddress))


def add_rack(rack):
    """Store a newly discovered rack in redis"""
    g.redis.sadd('racks', rack)
