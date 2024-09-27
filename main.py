import argparse
import logging

from config import DEFAULT_PORT, DEFAULT_CACHE_DURATION, DEFAULT_VERBOSE, LOG_FORMAT
from server import run_server

def setup_logging(verbose):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Run a CORS-enabled HTTP server for local development.",
        epilog="""
        This server enables CORS for specified origins and provides a proxy for remote requests.
        It's intended for local development only. Do not use in production.
        
        Usage example:
        python main.py -p 8000 -c 3600 -v
        """
    )
    parser.add_argument('-p', '--port', type=int, default=DEFAULT_PORT,
                        help=f"Port to run the server on (default: {DEFAULT_PORT})")
    parser.add_argument('-c', '--cache-duration', type=int, default=DEFAULT_CACHE_DURATION,
                        help=f"Cache duration in seconds (default: {DEFAULT_CACHE_DURATION})")
    parser.add_argument('-v', '--verbose', action='store_true', default=DEFAULT_VERBOSE,
                        help="Enable verbose output")
    return parser.parse_args()

def main():
    args = parse_arguments()
    setup_logging(args.verbose)
    run_server(args.port, args.cache_duration, args.verbose)

if __name__ == '__main__':
    main()