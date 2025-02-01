import sys
sys.path.insert(0, "../bla")

from bla import  Variables, proof
from bla.asserts import HALTS_ASSERT

# Declare domain - the set of variables used in the program
D = Variables("Vars", ["_"])

def loop():
    "begin" # while True
    if True: "begin"

proof([loop], D, assertions=[HALTS_ASSERT])



