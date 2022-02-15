import os
EXPECTED_DIR = os.path.join(os.path.dirname(__file__), 'test', 'expected')
DATA_DIR = os.path.join(os.path.dirname(__file__), 'test', 'data')
PROJECT_DIR = os.path.dirname(__file__)
RESULTS_DIR = os.path.join('test', 'outdump')
updateGroundTruthFile = False # This is to update the ground truth. It can take Value True or False