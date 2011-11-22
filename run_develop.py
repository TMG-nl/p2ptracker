#!/bin/env python
'''
Created on Feb 15, 2011

@author: ramon
'''
import sys
import os
from p2ptracker import create_app

if __name__ == "__main__":
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        app = create_app(sys.argv[1])
    else:
        app = create_app()
    assert app.config["HOST"]
    assert app.config["PORT"]
    assert app.config["DEBUG"]
    app.run(
        host=app.config["HOST"],
        port=int(app.config["PORT"]),
        debug=app.config["DEBUG"]
    )
