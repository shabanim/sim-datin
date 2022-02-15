import csv
import numpy as np
import comms
from comms import *
import argparse

parser = argparse.ArgumentParser(description='Comms wrapper')
parser.add_argument('-c','--configfile', type=str)
args = parser.parse_args()
config_file = args.configfile

with open(config_file, mode='r') as infile:
    reader = csv.reader(infile)
    config_dict = {rows[0]:rows[1] for rows in reader}
# for i in config_dict:
#     print(i)
#     print(config_dict[i])


compute = comms.Comms_scaleout(config_dict)
out=compute.scaleout()
print(out)