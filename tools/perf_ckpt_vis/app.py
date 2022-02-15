"""
Visualizer script for perf change over time.
Usage:
    python tools/perf_ckpt_vis/app.py
    This will start the flask server that fetches the results from
    the artifactory and creates a rest endpoint to expose them.

Open tools/perf_ckpt_vis/index.html in your favorite browser to view
the results. The default port for this application is 5000 and the UI
expects the APIs to be available on http://127.0.0.1:5000

Please find the prerequisites to run this script in
tools/perf_ckpt_vis/Readme.txt

"""
import os
import shutil
import sys
import platform
import pandas as pd
from pathlib import Path

from flask import Flask, request, jsonify, make_response

if platform.system() == 'Windows':
    sys.path.append(os.getcwd())
from pup import artifacts

app = Flask(__name__)

os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'development'
data_dir = Path('perf-tracking')


def _build_cors_prelight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response


def _corsify_actual_response(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response


def sanitize_str(input: str):
    return input.strip("\"")


def unzip_dir(zip_file='perf-tracking.zip', extract_dir='perf-tracking'):
    # shutil uses zipfile module that has compatibility issues when
    # unzipping a file zipped on Windows. This script will run only
    # on Linux machines so should be fine.

    dirpath = Path(extract_dir)
    if dirpath.exists() and dirpath.is_dir():
        shutil.rmtree(dirpath)

    try:
        shutil.unpack_archive(zip_file, extract_dir, 'zip')
    except Exception as e:
        print("ERROR: Unable to unzip %s ." % zip_file)
        print(e)


# @app.before_first_request
def init():
    artifacts(dl_perftracking=True)
    unzip_dir()
    global data_dir
    data_dir = Path("perf-tracking")


@app.route('/', methods=['GET'])
def get_netw_and_cfg_list():
    print("INFO: Request received: " + request.url)

    if request.method == "OPTIONS":  # CORS preflight
        return _build_cors_prelight_response()

    changes_dir = data_dir / "changes"

    dirs = os.listdir(changes_dir)
    response = {"data": {}}
    response["data"]["configs"] = dirs
    networks = set()
    for dir in dirs:
        netws = os.listdir(changes_dir / dir)
        networks.update(netws)

    response["data"]["networks"] = list(networks)
    return _corsify_actual_response(jsonify(response))


@app.route('/perfdata', methods=['GET'])
def get_change_data_for_netw_cfg():
    print("INFO: Request received: " + request.url)

    if request.method == "OPTIONS":  # CORS preflight
        return _build_cors_prelight_response()

    query_cfg = sanitize_str(request.args.get('config'))
    query_netw = sanitize_str(request.args.get('network'))

    hist_file = data_dir / "changes" / query_cfg / query_netw / "History.csv"
    print("INFO: Extracting data from: %s" % hist_file)

    if not os.path.exists(hist_file):
        response = {'errorMsg': 'Data unavailable for the requested combination.'}
        response = jsonify(response)
        return _corsify_actual_response(response), 400

    df = pd.read_csv(hist_file)
    batches = df['Batch'].unique()
    response = {'data': []}
    for batch in batches:
        temp = dict()
        temp['batch'] = int(batch)
        temp['history_data'] = []
        filtered_df = df[df['Batch'] == batch]
        cnt = 1
        for _, row in filtered_df.iterrows():
            fps_data = dict()
            fps_data['idx'] = cnt
            fps_data['ts'] = row['recorded_at']
            fps_data['commit_id'] = row['commit_id']
            fps_data['fps'] = int(row['FPS'])

            temp['history_data'].append(fps_data)
            cnt += 1

        response['data'].append(temp)

    return _corsify_actual_response(jsonify(response))


if __name__ == "__main__":
    # Legacy way of running flask applications.
    # Required to enable running this script from root dir
    init()
    app.run()
