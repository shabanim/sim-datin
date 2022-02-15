#!/usr/bin/env python
import os
import sys
import argparse
import csv
from pprint import pprint

def read_config(fname):
    with open(fname) as fin:
        reader = csv.reader(fin)
        return {row[0]: row[1] for row in reader}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', help='config file name')
    parser.add_argument('--override', help='override config file')
    parser.add_argument('--value', action='append', help='single variable override')
    args = parser.parse_args()
    print("Original config name:",args.config)
    basecfg = read_config(args.config)
    output_config = ('..'+args.config.strip('base_config_scaleout.csv')+'config_scaleout.csv')
    print("Updated config name:",output_config)
    print("")
    print("-----------------------------------------------------")

    if args.override:
        overridecfg = read_config(args.override)
        wrong_keys = {x for x in overridecfg if x not in basecfg}
        if wrong_keys:
            print('error: parameters {} not in configuration'.format(','.join(wrong_keys)))
            exit(1)
        basecfg.update(overridecfg)

    if args.value:

        for value in args.value[0].split(','):
            fields = value.split('=')
            assert len(fields) == 2
            if fields[0] not in basecfg:
                print('error: parameter {} not in configuration'.format(fields[0]))
                exit(1)
            print("Original value for ",fields[0]," is",basecfg[fields[0]])
            basecfg[fields[0]] = fields[1]
            print("Updated value for ", fields[0], " is", basecfg[fields[0]])
            print("-----------------------------------------------------")

    # All overrides applied at this point
    #pprint(basecfg)
    with open(output_config, 'w') as f:
        for key in basecfg.keys():
            f.write("%s,%s\n"%(key,basecfg[key]))



if __name__ == '__main__':
    exit(main())
