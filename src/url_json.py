from argparse import ArgumentParser
from time import time
from urllib.request import urlopen

import json


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--prefix', default='url_json')
    parser.add_argument('--url', default='http://localhost/')
    parser.add_argument(
        '--key',
        action='append',
        dest='keys', )
    return parser.parse_args()


def main():
    args = parse_args()
    response = urlopen(args.url)
    data = json.loads(response.read().decode('utf-8'))

    template = args.prefix + '.{} {}' + str(int(time()))

    for key, value in data.items():
        if key in args.keys or not args.keys:
            print(template.format(key, value))


if __name__ == '__main__':
    main()
