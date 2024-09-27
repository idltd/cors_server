import argparse
import logging

from config import DEFAULT_PORT, DEFAULT_CACHE_DURATION, LOG_FORMAT, LOG_LEVEL
from server import run_server

def setup_logging():
    logging.basicConfig(format=LOG_FORMAT, level=LOG_LEVEL)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run a CORS-enabled HTTP server for local development.",
        epilog="""
        This server enables CORS for specified origins and provides a proxy for remote requests.
        It's intended for local development only. Do not use in production.
        
        Usage example:
        python main.py -p 8000 -c 3600
        """
    )
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT,
                        help=f"Port to run the server on (default: {DEFAULT_PORT})")
    parser.add_argument('-c', '--cache-duration', type=int, default=DEFAULT_CACHE_DURATION,
                        help=f"Cache duration in seconds (default: {DEFAULT_CACHE_DURATION})")
    return parser.parse_args()

def main():
    setup_logging()
    args = parse_arguments()
    run_server(args.port, args.cache_duration)

if __name__ == '__main__':
    main()