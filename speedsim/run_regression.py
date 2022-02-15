#!/p/dpg/arch/perfhome/python/miniconda3/bin/python3 -u
"""
Running all tests discovered under current directory
"""
import getpass
import unittest
from io import StringIO
from pprint import pprint

print("Running as:", getpass.getuser())

test_paths = ['./asap/test', './pnets/test', './reports/test', './test']
for path in test_paths:
    loader = unittest.TestLoader()
    tests = loader.discover(path)

    stream = StringIO()
    runner = unittest.TextTestRunner(stream=stream)
    try:
        result = runner.run(tests)
        print('Tests run ', result.testsRun)
        print('Errors ', result.errors)
        pprint(result.failures)
        stream.seek(0)
        print('Test output\n', stream.read())

        if result.errors or result.failures:
            exit(-1)
    except:  # noqa: E722
        exit(-1)
