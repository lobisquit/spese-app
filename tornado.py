from spese_app.controller import app

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import os

http_server = HTTPServer(WSGIContainer(app))
# request system to free port for server
port = int(os.environ.get("PORT", 5000))
http_server.listen(port)
IOLoop.instance().start()
