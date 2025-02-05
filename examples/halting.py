import sys

sys.path.insert(0, "../bla")

from bla import proof
from bla.asserts import HALTS_ASSERT


def loop():
    while True:
        pass


proof([loop], domain={}, assertions=[HALTS_ASSERT])
