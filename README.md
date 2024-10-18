usage: main.py [-h] [-p PORT] [-c CACHE_DURATION] [-v] [-d]

Run a CORS-enabled HTTP server for local development.
<pre>
options:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  Port to run the server on (default: 8000)
  -c CACHE_DURATION, --cache-duration CACHE_DURATION
                        Cache duration in seconds (default: 3600)
  -v, --verbose         Enable verbose output (program flow)
  -d, --debug           Enable debug output (detailed content)
</pre>
This server enables CORS for specified origins and provides a proxy for remote requests. It's intended for local
development only. Do not use in production.
