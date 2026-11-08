"""Run the bundled topology/program/clearance regressions from any cwd.

Ordinary Python standard library; test-owned temporary SVG files only.
"""
from pathlib import Path
import unittest

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    suite=unittest.defaultTestLoader.discover(str(root/'tests'),top_level_dir=str(root))
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
