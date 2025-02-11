# In case you don't know what it is:
# https://www.youtube.com/watch?v=6cAbgAaEOVE

import sys

sys.path.insert(0, "../bla")

from bla import proof

domain = dict(
    small=[0, 1, 2, 3],
    large=[0, 1, 2, 3, 5],  # Note: omitted 4
)


def fill_small():
    while True:
        small = 3


def fill_large():
    while True:
        large = 5


def empty_small():
    while True:
        small = 0


def empty_large():
    while True:
        large = 0


def small_to_large():
    while True:
        small, large = (
            (0, small + large) if small + large <= 5 else (small - (5 - large), 5)
        )


def large_to_small():
    while True:
        small, large = (
            (small + large, 0) if small + large <= 3 else (3, large - (3 - small))
        )


proof(
    [fill_small, fill_large, empty_small, empty_large, small_to_large, large_to_small],
    domain,
)
