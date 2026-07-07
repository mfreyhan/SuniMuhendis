"""Make the src-layout ``sunimuhendis`` package importable in tests without
requiring an editable install (belt-and-suspenders alongside ``pip install -e .``)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
