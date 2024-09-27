import logging
from http.server import HTTPServer
import urllib.parse
from typing import Type

from config import DEFAULT_PORT
from handlers import BaseHandler, LocalFileHandler, RemoteProxyHandler

logger = logging.getLogger(__name__)

class CORSProxyServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, cache_duration=None):
        self.cache_duration = cache_duration
        super().__init__(server_address, RequestHandlerClass)

    def finish_request(self, request, client_address):
        parsed_path = urllib.parse.urlparse(self.RequestHandlerClass.path)
        if parsed_path.path.startswith('/proxy'):
            handler = RemoteProxyHandler(request, client_address, self, cache_duration=self.cache_duration)
        else:
            handler = LocalFileHandler(request, client_address, self, cache_duration=self.cache_duration)

def run_server(port: int = DEFAULT_PORT, cache_duration: int = None):
    server_address = ('', port)
    handler = BaseHandler
    
    try:
        with CORSProxyServer(server_address, handler, cache_duration) as httpd:
            logger.info(f"Serving CORS-enabled server on port {port}")
            logger.info(f"Use http://localhost:{port}/proxy?url=YOUR_URL as your proxy URL")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")