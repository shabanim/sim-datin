Visualizer script for perf change over time.

Usage:
    python tools/perf_ckpt_vis/app.py
    This will start the flask server that fetches the results from
    the artifactory and creates a rest endpoint to expose them.

Open tools/perf_ckpt_vis/index.html in your favorite browser to view
the results. The default port for this application is 5000 and the UI
expects the APIs to be available on http://127.0.0.1:5000

Requires -
- flask=1.1.2
    python -m pip install flask=1.1.2 OR
    conda install flask=1.1.2


