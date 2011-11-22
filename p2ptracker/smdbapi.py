"""This module handles all communication with the smdb api"""

import logging
import urllib2
import simplejson as json
from flask import current_app

log = logging.getLogger("hyves.p2ptracker.smdbapi")

def get_hostname_for_ipaddress(ipaddress):
    return _get_smdb_serverdata(ipaddress)['name']

def _get_smdb_serverdata(ipaddress):
    """
    Returns a dict with json data from the servermanagement api based on
    ipaddress query
    """
    apiurl = "%s/servers/ipaddresses/%s" % (current_app.config["SMDB_URL"], ipaddress)
    log.debug("my apiurl: %s" % apiurl)
    obj_dict = json.load(urllib2.urlopen(apiurl))
    log.debug("%s" % obj_dict)
    return obj_dict

def get_rack(peer):
    resp_d = _get_smdb_serverdata(peer)
    if len(resp_d.keys()) > 1:
        log.critical("The smdb-api returned more than one host for ipaddress: %s" % peer)
        log.critical("This is very serious data issue, please fix this")
        log.critical("returned data: %s" % resp_d)
        log.critical("defaulting to the last returned host")
    rack = ''
    for server in resp_d:
        rack = resp_d[server]['cabinet']
    return rack
