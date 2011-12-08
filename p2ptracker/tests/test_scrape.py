"""
https://github.com/hyves-org/p2ptracker
Copyright (c) 2011, Ramon van Alteren
MIT license: http://www.opensource.org/licenses/MIT
"""

from flaskext.testing import TestCase
from p2ptracker import create_app as mycreate_app

class TestScrape(TestCase):


    def create_app(self):
        return mycreate_app()

    def test_without_parameter(self):
        '''Test scrape url without info_hash'''
        resp = self.client.get('/scrape/')
        self.assertStatus(resp, 501)

    def test_with_parameter(self):
        '''Test scrape with an info_hash apram'''
        resp = self.client.get('/scrape/%13L%B2%81%DDT%02%1B%BF%D1l%B9%C6%25%1E%CD-g%DC%BF.json')
        self.assertStatus(resp, 501)
