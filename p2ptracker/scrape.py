"""""
To be implemented, scrape support
"""""

from flask import Module, abort

scrape = Module(__name__, url_prefix='/scrape')

@scrape.route('/', methods=["GET"])
@scrape.route('/<info_hash>.<ext>', methods=["GET"])
def rest_scrape(info_hash=None, ext='json'):
    """""Return scrape stats in the official bitorrent form"""""
    return abort(501, 'not implemented')

