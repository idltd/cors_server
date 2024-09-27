import logging
from http.server import HTTPServer
import urllib.parse
from typing import Type, Tuple, Any

from config import DEFAULT_PORT
from handlers import BaseHandler, LocalFileHandler, RemoteProxyHandler

logger = logging.getLogger(__name__)

class CORSProxyServer(HTTPServer):
    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass: Type[BaseHandler], 
                 cache_duration: int = None, verbose: bool = False, debug: bool = False):
        self.cache_duration = cache_duration
        self.verbose = verbose
        self.debug = debug
        super().__init__(server_address, RequestHandlerClass)

    def finish_request(self, request: Any, client_address: Tuple[str, int]) -> None:
        try:
            handler = self.RequestHandlerClass(request, client_address, self)
            
            if hasattr(handler, 'path'):
                if self.verbose:
                    logger.info(f"Processing request for path: {handler.path}")
                if handler.path.startswith('/proxy'):
                    RemoteProxyHandler(request, client_address, self, 
                                       cache_duration=self.cache_duration, 
                                       verbose=self.verbose, 
                                       debug=self.debug)
                else:
                    LocalFileHandler(request, client_address, self, 
                                     cache_duration=self.cache_duration, 
                                     verbose=self.verbose, 
                                     debug=self.debug)
            else:
                logger.warning("Handler does not have 'path' attribute. Using default BaseHandler.")
                BaseHandler(request, client_address, self)
        except Exception as e:
            logger.error(f"Error in finish_request: {str(e)}")
            BaseHandler(request, client_address, self)

def run_server(port: int = DEFAULT_PORT, cache_duration: int = None, 
               verbose: bool = False, debug: bool = False) -> None:
    server_address = ('', port)
    
    try:
        with CORSProxyServer(server_address, BaseHandler, cache_duration, verbose, debug) as httpd:
            logger.info(f"Serving CORS-enabled server on port {port}")
            logger.info(f"Use http://localhost:{port}/proxy?url=YOUR_URL as your proxy URL")
            logger.info(f"To serve local files, use http://localhost:{port}/path/to/your/file")
            if verbose:
                logger.info("Verbose mode enabled")
            if debug:
                logger.info("Debug mode enabled")
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")