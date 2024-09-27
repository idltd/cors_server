import logging
import os
from http.server import SimpleHTTPRequestHandler
import urllib.parse
import subprocess
from typing import Tuple, Dict

from config import ALLOWED_ORIGINS, ALLOWED_METHODS, ALLOWED_HEADERS
from cache import Cache

logger = logging.getLogger(__name__)

class BaseHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.cache = Cache(kwargs.pop('cache_duration', None))
        self.verbose = kwargs.pop('verbose', False)
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        if self.verbose:
            logger.info(format % args)

    def end_headers(self):
        self.send_cors_headers()
        SimpleHTTPRequestHandler.end_headers(self)

    def send_cors_headers(self):
        for origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', ', '.join(ALLOWED_METHODS))
        self.send_header('Access-Control-Allow-Headers', ', '.join(ALLOWED_HEADERS))

    def do_GET(self):
        logger.info(f"Received GET request: {self.path}")
        logger.info(f"Request headers: {self.headers}")
        super().do_GET()

class LocalFileHandler(BaseHandler):
    def do_GET(self):
        logger.info(f"Processing local file request: {self.path}")
        path = self.path[1:] if self.path.startswith('/') else self.path
        if self.path.startswith('/proxy?url='):
            url = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['url'][0]
            path = urllib.parse.urlparse(url).path
            path = path[1:] if path.startswith('/') else path

        full_path = os.path.join(os.getcwd(), path)
        if os.path.exists(full_path):
            logger.info(f"Serving local file: {full_path}")
            with open(full_path, 'rb') as file:
                content = file.read()
            self.send_response(200)
            self.send_header('Content-type', self.guess_type(path))
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
            logger.info(f"Successfully served local file: {full_path}")
        else:
            logger.warning(f"Local file not found: {full_path}")
            self.send_error(404, "File not found")

class RemoteProxyHandler(BaseHandler):
    def do_GET(self):
        logger.info(f"Processing remote proxy request: {self.path}")
        url = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['url'][0]
        logger.info(f"Proxying remote request to: {url}")

        cached_content = self.cache.read_cache(url)
        if cached_content:
            logger.info(f"Serving cached content for: {url}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', len(cached_content))
            self.send_header('X-Served-From', 'cache')
            self.end_headers()
            self.wfile.write(cached_content)
            logger.info(f"Successfully served cached content for: {url}")
            return

        try:
            status_code, headers, content = self.fetch_url(url)
            self.send_response(status_code)
            for key, value in headers:
                if key.lower() not in ('transfer-encoding', 'content-encoding'):
                    self.send_header(key, value)
            self.send_header('X-Served-From', 'origin')
            self.end_headers()
            self.wfile.write(content)

            self.cache.write_cache(url, content)
            logger.info(f"Successfully proxied and cached {len(content)} bytes for {url}")
        except Exception as e:
            logger.error(f"Error proxying request to {url}: {str(e)}")
            self.send_error(500, f"Error proxying request: {str(e)}")

    def fetch_url(self, url: str) -> Tuple[int, Dict[str, str], bytes]:
        logger.info(f"Fetching URL: {url}")
        parsed_url = urllib.parse.urlparse(url)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
        curl_command = ['curl', '-s', '-i', '-H', f'Origin: {origin}', url]
        
        logger.debug(f"Executing curl command: {' '.join(curl_command)}")
        result = subprocess.run(curl_command, capture_output=True, check=True)
        output = result.stdout.decode('utf-8', errors='ignore')
        
        headers, _, content = output.partition('\r\n\r\n')
        status_line, *header_lines = headers.split('\n')
        status_code = int(status_line.split()[1])
        
        parsed_headers = [line.split(': ', 1) for line in header_lines if line]
        logger.info(f"Received response from {url}: status={status_code}, headers={parsed_headers}")
        return status_code, parsed_headers, content.encode('utf-8')