import logging
from http.server import HTTPServer
from typing import Type, Tuple, Any

from config import DEFAULT_PORT
from handlers import BaseHandler

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
            BaseHandler(request, client_address, self, 
                        cache_duration=self.cache_duration, 
                        verbose=self.verbose, 
                        debug=self.debug)
        except Exception as e:
            logger.error(f"Error in finish_request: {str(e)}")

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