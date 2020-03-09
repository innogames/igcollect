import argparse
import datetime
import time
import socket

from subprocess import run, PIPE


def parse_args():
    parser = argparse.ArgumentParser(
        description='Script to collect statuscodes from nginx')
    parser.add_argument('-l', '--logfile',
                        help='path to logfile')
    parser.add_argument('-s', '--software', default='nginx',
                        help='witch tool is using it (example: nginx)')
    parser.add_argument('-a', '--addon', default='',
                        help='additional awk conditions')
    parser.add_argument('-x', '--position', type=int, default=9,
                        help='were to search for the code in the log file '
                             '(default= 9 nginx access.log)')
    parser.add_argument('-t', '--time', type=int, default=1,
                        choices=range(1, 5),
                        help='the interval in (full)minutes the script runs.'
                             'has to be the same time as the corresponding '
                             'cronjob! '
                             '(default= 1)')
    parser.add_argument('-p', '--prefix',
                        default='servers.{}.software.{}'.format(
                            socket.gethostname().replace('.', '_'),
                            parser.parse_args().software),
                        help='the path to the value in Graphite '
                             '(default= servers.(hostname).software.'
                             '(software).status_codes)')
    return parser.parse_args()


def cmdline(command):
    process = run(
        command,
        stdout=PIPE,
        stderr=PIPE,
        universal_newlines=True,
        shell=True
    )
    return process.stdout


def main():
    args = parse_args()
    prob_time = int(time.time())
    #search_time = datetime.datetime.utcnow()
    search_time = datetime.datetime.strptime('09/Mar/2020:10:00:33', '%d/%b/%Y:%H:%M:%S')

    errors = {}

    for i in range(0, 60 * args.time):
        temp_search_time = (search_time - datetime.timedelta(
            seconds=i)).strftime('%d/%b/%Y:%H:%M:%S')

        resaults = cmdline('grep {} {} | awk {}| sort | uniq -c'.format(
            temp_search_time, args.logfile,"'{print $9}'")).split('\n')

        if resaults != ['']:
            for result in resaults:
                result = result.strip().split()
                if result != []:
                    if result[1] not in errors.keys():
                        errors[result[1]] = int(result[0])
                    else:
                        errors[result[1]] += int(result[0])

    template = args.prefix + '{}.{} {} {}'

    total = 0
    for key in errors.keys():
        print(template.format('.status_codes', key, errors[key], prob_time))
        total += errors[key]

    print(template.format('', 'requests', total, prob_time))



if __name__ == '__main__':
    main()