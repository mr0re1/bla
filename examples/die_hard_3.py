# In case you don't know what it is:
# https://www.youtube.com/watch?v=6cAbgAaEOVE

import sys

sys.path.insert(0, "../bla")

from bla import proof

domain = dict(
  small=[0, 1, 2, 3],
  large=[0, 1, 2, 3, 5], # Note: omitted 4
)


def fill_small():
  while True:
    small = 3

def fill_large():
  while True:
    large = 5

def pour_small():
  while True:
    small = 0

def pour_large():
  while True:
    large = 0

def small_to_large():
  while True:
    with atomic:
      if small + large <= 5:
        large = small + large
        small = 0
      else:
        small = small - (5 - large)
        large = 5
        

def large_to_small():
  while True:
    with atomic:
      if small + large <= 3:
        small = small + large
        large = 0
      else:
        large = large - (3 - small)
        small = 3
        

proof([fill_small, fill_large, pour_small, pour_large, small_to_large, large_to_small], domain)