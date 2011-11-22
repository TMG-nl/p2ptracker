#!/usr/bin/env python
import sys
import os
from p2ptracker import create_app
from cherrypy import wsgiserver

if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        app = create_app(sys.argv[1])
    else:
        app = create_app()
    assert app.config["HOST"]
    assert app.config["PORT"]
    if int(app.config["PORT"]) < 1025:
        if not os.getuid() == 0:
            sys.exit("Only root can run this script for ports < 1025, you requested %s" % app.config['PORT'], status=1)
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(bind_addr=(app.config["HOST"], int(app.config["PORT"])), wsgi_app=d, numthreads=20, request_queue_size=10)
    try:
        server.start()
    except KeyboardInterrupt, e:
        server.stop()
