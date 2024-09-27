import argparse
import logging

from config import DEFAULT_PORT, DEFAULT_CACHE_DURATION, LOG_FORMAT
from server import run_server

def setup_logging(verbose, debug):
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    
    logging.basicConfig(level=level, format=LOG_FORMAT)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run a CORS-enabled HTTP server for local development.",
        epilog="""
        This server enables CORS for specified origins and provides a proxy for remote requests.
        It's intended for local development only. Do not use in production.
        """
    )
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT,
                        help=f"Port to run the server on (default: {DEFAULT_PORT})")
    parser.add_argument('-c', '--cache-duration', type=int, default=DEFAULT_CACHE_DURATION,
                        help=f"Cache duration in seconds (default: {DEFAULT_CACHE_DURATION})")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Enable verbose output (program flow)")
    parser.add_argument('-d', '--debug', action='store_true',
                        help="Enable debug output (detailed content)")
    return parser.parse_args()

def main():
    args = parse_arguments()
    setup_logging(args.verbose, args.debug)
    run_server(args.port, args.cache_duration, args.verbose, args.debug)

if __name__ == '__main__':
    main()