import os
import subprocess
import sys

from unittest import TestCase


class LintTest(TestCase):
    """
    Runs flake8 to check syntax compliance.
    NOTE: Use # noqa in command line to filter cases.
    NOTE: For a naming convention testing install pep8-naming before running this test
    """
    FLAKE = os.path.join(os.path.dirname(sys.executable), "Scripts", "flake8.exe")

    def test_lint(self):
        root = os.path.dirname(os.path.dirname(__file__))

        print("\n")
        self.assertTrue(os.path.exists(LintTest.FLAKE), msg='Please install flake8 for lint test to work properly!')
        cmd = [
            LintTest.FLAKE,
            '--max-line-length=150',
            '--exclude=old_gui,requests,T2M,examples,snakes,compiler.py,dist,build,local_site_packages,arch_power',
            root
        ]
        subprocess.check_call(cmd)
