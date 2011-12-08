"""
https://github.com/hyves-org/p2ptracker
Copyright (c) 2011, Ramon van Alteren
MIT license: http://www.opensource.org/licenses/MIT
"""

from flask import Flask, Request, g, current_app
from werkzeug.contrib.fixers import ProxyFix
import os
import redis
import logging

log = logging.getLogger("hyves.p2ptracker.init")

class Latin1Request(Request):
    url_charset = 'latin-1'

def redis_connect():
    redishost = current_app.config["REDISHOST"]
    redisport = current_app.config["REDISPORT"]
    g.redis = redis.Redis(host=redishost, port=redisport, db=0)

def create_app(configfilename=None):
    """Loads the configfilename in the app.config object as requested"""
    setup_logging()
    log.debug('creating application')
    app = Flask(__name__)
    setup_config(app, configfilename)
    setup_modules(app)
    setup_aux(app)
    # If we run behind nginx, fix the request vars
    if app.config['PROXYPASS']:
        log.debug("Loading proxy fix")
        app.wsgi_app = ProxyFix(app.wsgi_app)
    else:
        log.debug("Running without proxy fix")
    # bittorrent clients live in the stone age
    app.request_class = Latin1Request
    log.debug('setup request class')
    # Register the redis connect before every request
    app.before_request(redis_connect)
    log.debug('assigned before_request')
    return app

def setup_config(app, configfilename=None):
    """Load the configuration for this app"""
    log.debug('setup configuration')
    app.config.from_object('%s.defaultconfig' % __name__)
    if configfilename:
        app.config.from_pyfile(configfilename)
    if 'P2PTRACKERCONFIG' in os.environ:
        app.config.from_envvar('P2PTRACKERCONFIG')

def setup_modules(app):
    from p2ptracker.announce import announce
    from p2ptracker.transfers import transfers
    from p2ptracker.scrape import scrape
    from p2ptracker.torrents import torrents
    app.register_module(announce)
    app.register_module(transfers)
    app.register_module(scrape)
    app.register_module(torrents)
    log.debug('loaded modules')


def setup_logging():
    log = logging.getLogger("hyves.p2ptracker")
    fmt = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    hnd = logging.FileHandler('p2ptracker.log')
    hnd.setFormatter(fmt)
    log.addHandler(hnd)
    log.setLevel(logging.DEBUG)
    log.debug('set up logging')

def setup_aux(app):
    if not os.path.exists(app.config['UPLOAD_PATH']):
        os.makedirs(app.config['UPLOAD_PATH'])
    log.debug('loaded aux setup stuff')

