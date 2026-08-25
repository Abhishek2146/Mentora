"""Pytest configuration -- ensures the backend package root is importable."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
