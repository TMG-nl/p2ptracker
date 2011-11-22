__author__ = 'ramon'

from p2ptracker.tests.helpers import utils

def setUp():
    utils.start_redis_server()

def tearDown():
    utils.stop_redis_server()

