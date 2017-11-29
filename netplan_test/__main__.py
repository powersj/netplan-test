"""Program entry point and arg parser."""
import argparse
import logging
import sys

from . import runner


def main():
    """Entry point for cloud test suite."""
    parser = argparse.ArgumentParser(prog='netplan-test')
    subparsers = parser.add_subparsers(dest='subcmd')
    subparsers.required = True

    run = subparsers.add_parser('run')
    collect = subparsers.add_parser('collect')
    verify = subparsers.add_parser('verify')
    verify.add_argument('--results',
                        help='Results dir to run tests against')
    verify.add_argument('--verbose',
                        action='store_true',
                        help='Enable verbose output')

    # collect and run use same arguments, but run calls verify as well
    for subparser in [run, collect]:
        subparser.add_argument('--results',
                               dest='results_dir',
                               help='Results dir to store collected data')
        subparser.add_argument('--test',
                               dest='tests',
                               action='append',
                               help='Test to run, otherwise all in configs')
        subparser_group = subparser.add_mutually_exclusive_group()
        subparser_group.add_argument('--release',
                                     help='Ubuntu release to use')
        subparser_group.add_argument('--image',
                                     help='Path to image to use')
        subparser_group.add_argument('--verbose',
                                     action='store_true',
                                     help='Enable verbose output')

    args = parser.parse_args()

    # Setup and configure logging
    verbose = vars(args).pop('verbose')
    log_level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger('netplan_test')
    logger.setLevel(log_level)

    handler = logging.StreamHandler()
    log_format = '[%(asctime)s] %(levelname)8s: %(message)s'
    handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(handler)

    # Launch subcommand
    cmd = vars(args).pop('subcmd')
    arguments = vars(args)

    return {
        'run': runner.run,
        'collect': runner.collect,
        'verify': runner.verify,
    }[cmd](**arguments)


if __name__ == "__main__":
    sys.exit(main())
