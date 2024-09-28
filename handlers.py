import logging
import os
from http.server import SimpleHTTPRequestHandler
import urllib.parse
import subprocess
from typing import Tuple, Dict
import html
import sys
import io
from pathlib import Path 

from config import ALLOWED_ORIGINS, ALLOWED_METHODS, ALLOWED_HEADERS
from cache import Cache

logger = logging.getLogger(__name__)

class BaseHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.cache = Cache(kwargs.pop('cache_duration', None))
        self.verbose = kwargs.pop('verbose', False)
        self.debug = kwargs.pop('debug', False)
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        if self.verbose or self.debug:
            logger.info(format % args)

    def do_GET(self):
        if self.verbose:
            logger.info(f"Received GET request: {self.path}")
        if self.debug:
            logger.debug(f"GET request headers: {self.headers}")

        if self.path.startswith('/proxy'):
            self.handle_proxy_request()
        else:
            self.handle_local_request()

    def handle_local_request(self):
        if self.verbose:
            logger.info(f"Handling local file request: {self.path}")
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            if self.verbose:
                logger.info(f"Request is for a directory: {path}")
            for index in "index.html", "index.htm":
                index_path = os.path.join(path, index)
                if os.path.exists(index_path):
                    path = index_path
                    break
            else:
                if self.verbose:
                    logger.info("No index file found, sending directory listing")
                return self.list_directory(path)

        try:
            with open(path, 'rb') as f:
                content = f.read()
                self.send_response(200)
                self.send_header("Content-type", self.guess_type(path))
                self.send_header("Content-Length", len(content))
                self.end_headers()
                self.wfile.write(content)
            if self.verbose:
                logger.info(f"Successfully served local file: {path}")
            if self.debug:
                logger.debug(f"File content (first 100 bytes): {content[:100]}")
        except IOError:
            self.send_error(404, "File not found")
            if self.verbose:
                logger.warning(f"Local file not found: {path}")
    
    def handle_proxy_request(self):
        if self.verbose:
            logger.info("Handling proxy request")
        
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if 'url' not in params:
            self.send_error(400, "Missing 'url' parameter")
            if self.verbose:
                logger.warning("Proxy request missing 'url' parameter")
            return

        url = params['url'][0]
        parsed_url = urllib.parse.urlparse(url)
        
        if not parsed_url.scheme:
            # No protocol, treat as local file
            if self.verbose:
                logger.info(f"No protocol in URL, serving local file: {url}")
            self.path = '/' + url  # Prepend '/' to make it a valid path
            return self.handle_local_request()

        if self.verbose:
            logger.info(f"Proxying request to: {url}")
        cached_content = self.cache.read_cache(url)
        if cached_content:
            if self.verbose:
                logger.info(f"Serving cached content for: {url}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', len(cached_content))
            self.send_header('X-Served-From', 'cache')
            self.end_headers()
            self.wfile.write(cached_content)
            if self.debug:
                logger.debug(f"Cached content (first 100 bytes): {cached_content[:100]}")
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
            if self.verbose:
                logger.info(f"Successfully proxied and cached {len(content)} bytes for {url}")
            if self.debug:
                logger.debug(f"Proxied content (first 100 bytes): {content[:100]}")
        except Exception as e:
            self.send_error(500, f"Error proxying request: {str(e)}")
            logger.error(f"Error proxying request to {url}: {str(e)}")

    def fetch_url(self, url: str) -> Tuple[int, Dict[str, str], bytes]:
        if self.verbose:
            logger.info(f"Fetching URL: {url}")
        parsed_url = urllib.parse.urlparse(url)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
        curl_command = ['curl', '-s', '-i', '-H', f'Origin: {origin}', url]
        
        if self.debug:
            logger.debug(f"Executing curl command: {' '.join(curl_command)}")
        result = subprocess.run(curl_command, capture_output=True, check=True)
        output = result.stdout.decode('utf-8', errors='ignore')
        
        headers, _, content = output.partition('\r\n\r\n')
        status_line, *header_lines = headers.split('\n')
        status_code = int(status_line.split()[1])
        
        parsed_headers = [line.split(': ', 1) for line in header_lines if line]
        if self.verbose:
            logger.info(f"Received response from {url}: status={status_code}")
        if self.debug:
            logger.debug(f"Response headers: {parsed_headers}")
        return status_code, parsed_headers, content.encode('utf-8')

    def end_headers(self):
        self.send_cors_headers()
        SimpleHTTPRequestHandler.end_headers(self)

    def send_cors_headers(self):
        for origin in ALLOWED_ORIGINS:
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Access-Control-Allow-Headers', ', '.join(ALLOWED_HEADERS))

    def list_directory(self, path):
        path = Path(path)
        if self.verbose:
            logger.info(f"Listing directory: {path}")
        try:
            list = os.listdir(path)
        except OSError:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        r = []
        try:
            displaypath = urllib.parse.unquote(self.path, errors='surrogatepass')
        except UnicodeDecodeError:
            displaypath = urllib.parse.unquote(str(path))
        displaypath = html.escape(displaypath, quote=False)
        enc = sys.getfilesystemencoding()
        title = 'Directory listing for %s' % displaypath
        r.append('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" '
                 '"http://www.w3.org/TR/html4/strict.dtd">')
        r.append('<html>\n<head>')
        r.append('<meta http-equiv="Content-Type" '
                 'content="text/html; charset=%s">' % enc)
        r.append('<title>%s</title>\n</head>' % title)
        r.append('<body>\n<h1>%s</h1>' % title)
        r.append('<hr>\n<ul>')
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            r.append('<li><a href="%s">%s</a></li>'
                    % (urllib.parse.quote(linkname, errors='surrogatepass'),
                       html.escape(displayname, quote=False)))
        r.append('</ul>\n<hr>\n</body>\n</html>\n')
        encoded = '\n'.join(r).encode(enc, 'surrogateescape')
        f = io.BytesIO()
        f.write(encoded)
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", f"text/html; charset={enc}")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        return f

    def do_HEAD(self):
        if self.verbose:
            logger.info(f"Received HEAD request: {self.path}")
        if self.debug:
            logger.debug(f"HEAD request headers: {self.headers}")
        SimpleHTTPRequestHandler.do_HEAD(self)

    def do_POST(self):
        if self.verbose:
            logger.info(f"Received POST request: {self.path}")
        if self.debug:
            logger.debug(f"POST request headers: {self.headers}")
        self.send_error(405, "Method Not Allowed")

    def do_OPTIONS(self):
        if self.verbose:
            logger.info(f"Received OPTIONS request: {self.path}")
        if self.debug:
            logger.debug(f"OPTIONS request headers: {self.headers}")
        self.send_response(200)
        self.end_headers()