# https://en.wikipedia.org/wiki/Dekker%27s_algorithm
import sys

sys.path.insert(0, "../bla")


from bla import proof

D = {
    "wants_to_enter_0": False,
    "wants_to_enter_1": False,
    "turn": False,
    "critical_section_used": False,
}


def p0():
    wants_to_enter_0 = True
    while wants_to_enter_1:
        if turn == True:
            wants_to_enter_0 = False
            while turn == True:
                pass  # busy wait
            wants_to_enter_0 = True

    # critical section
    assert not critical_section_used
    critical_section_used = True
    critical_section_used = False
    # releasing critical section
    turn = True
    wants_to_enter_0 = False


def p1():
    wants_to_enter_1 = True
    while wants_to_enter_0:
        if turn == False:
            wants_to_enter_1 = False
            while turn == False:
                pass  # busy wait
            wants_to_enter_1 = True

    # critical section
    assert not critical_section_used
    critical_section_used = True
    critical_section_used = False
    # releasing critical section
    turn = False
    wants_to_enter_1 = False


# TODO: HALTS_ASSERT to do a better job
# proof([p0, p1], D, assertions=[HALTS_ASSERT])

proof([p0, p1], D)  # OK


def p1_brute():
    wants_to_enter_1 = True

    # critical section
    assert not critical_section_used
    critical_section_used = True
    critical_section_used = False
    # releasing critical section
    turn = False
    wants_to_enter_1 = False


proof([p0, p1_brute], D)
