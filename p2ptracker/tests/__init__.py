"""
https://github.com/hyves-org/p2ptracker
Copyright (c) 2011, Ramon van Alteren
MIT license: http://www.opensource.org/licenses/MIT
"""

from p2ptracker.tests.helpers import utils

def setUp():
    utils.start_redis_server()

def tearDown():
    utils.stop_redis_server()

