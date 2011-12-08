"""
https://github.com/hyves-org/p2ptracker
Copyright (c) 2011, Ramon van Alteren
MIT license: http://www.opensource.org/licenses/MIT

Various bits and pieces that don't fit comfortable anywhere else
"""

import logging
import socket
import struct
from flask import g

log = logging.getLogger("hyves.p2ptracker.utils")

def unique(seq):
    """This utility method comes straight out of the Python Cookbook 2nd edition recipe 18.1
    It returns the sequence removing any duplicate items, this depends of course on the sequence items actually implementing some form of 
    comparison. It tries three methods, fastest to slow. See recipe for discussion"""
    # Try convering to a set first, this is the fastest way to handle this
    try:
        return list(set(seq))
    except TypeError:
        pass
    # Since hashing apparently doesn't work, we'll sort and then weed out dups
    tlist = list(seq)
    try:
        tlist.sort()
    except TypeError:
        del tlist # Can't sort them either
    else:
        # Sort worked, now weed out the dups
        return [x for i, x in enumerate(tlist) if not i or x != tlist[i-1]]
    # We're left with the slowest brute force method
    tlist = []
    for item in seq:
        if item not in tlist:
            tlist.append(item)
    return tlist

def get_hash_hex(raw_hash):
    """Creates a nice hex representation of a raw req"""
    return raw_hash.encode('iso-8859-1').encode('hex')

def resolve_ipaddress(ipaddress):
    """Tries to resolve the ipaddress and return a hostname"""
    try:
        hostname = socket.getfqdn(socket.gethostbyaddr(ipaddress)[0])
        log.debug('setting hostname:%s for ipaddress:%s' % (hostname, ipaddress))
        return hostname
    except socket.herror, e:
        log.warning("Couldn't find hostname: %s" % e)
        return "UNKNOWN"

def to_bytes(n):
    return [chr(n & 255)] + to_bytes(n >> 8) if n > 0 else []

def convert_ipaddress_to_pack(ipaddress):
    return socket.inet_aton(ipaddress)

def convert_pack_to_ipaddress(pack):
    return socket.inet_ntoa(pack)

def convert_pack_to_integer(pack):
    (i, ) = struct.unpack('!h', pack)
    return i

def convert_integer_to_pack(integer):
    return struct.pack('!h', integer)

def get_ips_from_pack(pack):
    offset = len(pack)
    ips = []
    while offset > 0:
        ips.append(convert_pack_to_ipaddress(pack[offset-6:offset-2]))
        offset -= 6
    return ips


def is_active(ihash):
    """Return true if the transfer is active"""
    return g.redis.sismember("active_transfers", ihash)
