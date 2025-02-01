# https://en.wikipedia.org/wiki/Dekker%27s_algorithm
import sys
sys.path.insert(0, "../bla")


from bla import Variables, proof
from bla.asserts import HALTS_ASSERT

D = Variables("Vars", ["wants_to_enter_0", "wants_to_enter_1", "turn", "critical_section"])

def p0():
    wants_to_enter_0 = True
    while wants_to_enter_1:
      if turn == True:
         wants_to_enter_0 = False
         while turn == True:
            pass # busy wait
         wants_to_enter_0 = True

    # critical section
    assert critical_section == False
    critical_section = True
    critical_section = False
    # releasing critical section
    turn = True
    wants_to_enter_0 = False


def p1():
    wants_to_enter_1 = True
    while wants_to_enter_0:
        if turn == False:
            wants_to_enter_1 = False
            while turn == False:
                pass # busy wait
            wants_to_enter_1 = True

    # critical section
    assert critical_section == False
    critical_section = True
    critical_section = False
    # releasing critical section
    turn = False
    wants_to_enter_1 = False


# TODO: HALTS_ASSERT to do a better job
# proof([p0, p1], D, assertions=[HALTS_ASSERT])

proof([p0, p1], D) # OK


def p1_brute():
    wants_to_enter_1 = True
    
    # critical section
    assert critical_section == False
    critical_section = True
    critical_section = False
    # releasing critical section
    turn = False
    wants_to_enter_1 = False


proof([p0, p1_brute], D)
"""
...
def p0():                            | def p1_brute():                      | wants_to_enter_0=True
     wants_to_enter_0 = True          |     wants_to_enter_1 = True          | wants_to_enter_1=True
     while wants_to_enter_1 == True:  |                                      | turn=False
       if turn == True:               |     # critical section               | critical_section=True
          wants_to_enter_0 = False    |     assert critical_section == False |
          while turn == True:         |     critical_section = True          |
             pass # busy wait         | ->  critical_section = False         |
          wants_to_enter_0 = True     |     # releasing critical section     |
                                      |     turn = False                     |
     # critical section               |     wants_to_enter_1 = False         |
     assert critical_section == False |                                      |
 ->  critical_section = True          |                                      |
     critical_section = False         |                                      |
     # releasing critical section     |                                      |
     turn = True                      |                                      |
     wants_to_enter_0 = False         |                                      |
Assertion failed: p0:8: assert critical_section == False
"""