"""
This script fetches performance checkpoint data stored in the Jfrog artifactory
and stores it into a JavaScript file which is then visualized by the index.html
file in this directory.

NOTE: A temporary data.js file is created by this script necessary for visualization
but has been added to .gitignore

Instructions for running:
python3 visualizer.py
"""

import os
import json
import sys
import platform
import pandas as pd
import shutil

if platform.system() == 'Windows':
    sys.path.append(os.getcwd())
from pup import artifacts

ckpt_in = os.path.join('perf-tracking', 'perf_ckpt.csv')
ckpt_summary_in = os.path.join('perf-tracking', 'perf_ckpt_summary.json')
f_out = os.path.join('tools', 'perf_ckpt_vis', 'data.js')

# download the checkpoint files from artifactory
artifacts(dl_perftracking=True)

if not os.path.isdir("perf-tracking"):
    print("Unable to download perf-tracking files from Jfrog artifactory. \nMake sure Jfrog CLI is configured.")
    exit(-1)

df = pd.read_csv(ckpt_in)
configs = set()
networks = set()

temp_dict = {}
col_names = df.columns
for _, row in df.iterrows():
    if row['config'] not in temp_dict:
        temp_dict[row['config']] = {}
        configs.add(row['config'])

    temp_dict[row['config']][row['Network']] = {}
    networks.add(row['Network'])
    for col in col_names:
        if col not in ['config', 'Network']:
            temp_dict[row['config']][row['Network']][col] = row[col]

ckpt_dict_str = json.dumps(temp_dict)

ckpt_summary_str = "[]"
# Load summary data and write as string
with open(ckpt_summary_in) as f:
    ckpt_summary = json.load(f)

    # TODO: Some temporary hack cause of a bug which has been fixed.
    #   Remove if the checkpoint_summary file is ever reset
    if ckpt_summary[0]['comments'] == 'init':
        ckpt_summary[0]['params_affected'] = []

    ckpt_summary_str = json.dumps(ckpt_summary)

# write as a js file
with open(f_out, 'w') as f:
    f.write("latestResults = " + ckpt_dict_str + '\n')
    f.write("summaryData = " + ckpt_summary_str + '\n')
    f.write("configs = " + json.dumps(list(configs)) + '\n')
    f.write("networks = " + json.dumps(list(networks)) + '\n')
    f.write("kpi = " + json.dumps(list(col_names)) + '\n')

print("JS file with data written to: " + f_out)

# Remove the downloaded perf-tracking dir
shutil.rmtree('perf-tracking')
print("Removed perf-tracking dir as no longer required.")

print("Completed.")
