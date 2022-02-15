#!/usr/bin/env python
"""Script to convert from sparsity reported in Gary's models to
   ArchBench format"""

import csv
import yaml
import argparse
import sys

from collections import OrderedDict


def convert2dense(num):
    return (100 - float(num)) / 100


def main(in_args):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-i", "--input", help="Input CSV file", required=True, type=argparse.FileType('r'))
    parser.add_argument("-o", "--output", help="Output YAML file", required=True, type=argparse.FileType('w'))

    args = parser.parse_args(in_args)

    data = OrderedDict()
    reader = csv.DictReader(args.input)

    valid_header = ['Layer', 'Act', 'ActElop', 'Wght', 'Output']
    if set(valid_header) != set(reader.fieldnames):
        print("ERROR: CSV header shall be", str(valid_header), "instead it is", str(reader.fieldnames))
        return 1

    for row in reader:
        row = {k: v.strip() for k, v in row.items()}

        layer_name = row["Layer"]

        data[layer_name] = OrderedDict()

        if row["Act"]:
            data[layer_name]["Input"] = [convert2dense(row["Act"])]

        if row["ActElop"]:
            data[layer_name]["Input"].append(convert2dense(row["ActElop"]))

        if row["Wght"]:
            data[layer_name]["Parameters"] = [convert2dense(row["Wght"])]

        if row["Output"]:
            data[layer_name]["Output"] = [convert2dense(row["Output"])]

    yaml.dump(data, args.output, default_flow_style=False)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
