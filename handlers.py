import logging
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
        super().__init__(*args, **kwargs)

    def end_headers(self):
        self.send_cors_headers()
        SimpleHTTPRequestHandler.end_headers(self)

    def send_cors_headers(self):
        for origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
        self.send_header('Access-Control-Allow-Methods', ', '.join(ALLOWED_METHODS))
        self.send_header('Access-Control-Allow-Headers', ', '.join(ALLOWED_HEADERS))

class LocalFileHandler(BaseHandler):
    def do_GET(self):
        path = self.path[1:] if self.path.startswith('/') else self.path
        if self.path.startswith('/proxy?url='):
            url = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['url'][0]
            path = urllib.parse.urlparse(url).path
            path = path[1:] if path.startswith('/') else path

        logger.info(f"Serving local file: {path}")
        return SimpleHTTPRequestHandler.do_GET(self)

class RemoteProxyHandler(BaseHandler):
    def do_GET(self):
        url = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)['url'][0]
        logger.info(f"Proxying remote request to: {url}")

        cached_content = self.cache.read_cache(url)
        if cached_content:
            logger.info(f"Serving cached content for: {url}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.end_headers()
            self.wfile.write(cached_content)
            return

        try:
            status_code, headers, content = self.fetch_url(url)
            self.send_response(status_code)
            for key, value in headers:
                if key.lower() not in ('transfer-encoding', 'content-encoding'):
                    self.send_header(key, value)
            self.end_headers()
            self.wfile.write(content)

            self.cache.write_cache(url, content)
            logger.info(f"Successfully proxied and cached {len(content)} bytes for {url}")
        except Exception as e:
            logger.error(f"Error proxying request to {url}: {str(e)}")
            self.send_error(500, f"Error proxying request: {str(e)}")

    def fetch_url(self, url: str) -> Tuple[int, Dict[str, str], bytes]:
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
        return status_code, parsed_headers, content.encode('utf-8')