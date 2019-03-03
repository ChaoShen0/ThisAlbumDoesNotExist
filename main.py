#!/usr/bin/env python3

import argparse
import sys


def parse_args(argv):
    # declare our base argument parser
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')
    subparsers.required = True

    ### DATA
    data_parser = subparsers.add_parser('data')
    data_parser.add_argument('--playlist-file', type=str, required=True,
        help='The file containing playlist ids that we want to pull training data from')
    data_parser.add_argument('--output-dir', type=str, default='./data',
        help='The directory to output downloaded album artwork files')

    ### TRAIN
    train_subparser = subparsers.add_parser('train')


    ### TEST
    test_subparser = subparsers.add_parser('test')

    return parser.parse_args(argv)

if __name__ == '__main__':
    args = parse_args(sys.argv[1:])