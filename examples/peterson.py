# https://en.wikipedia.org/wiki/Peterson%27s_algorithm
import sys

sys.path.insert(0, "../bla")


from bla import proof

D = {
    "flag_0": False,
    "flag_1": False,
    "turn": [0, 1],
    "cs_used": False,
}


def p0():
    flag_0 = True
    turn = 1
    while flag_1 and turn == 1:
        pass  # busy wait
    # critical section
    assert not cs_used
    cs_used = True
    cs_used = False
    turn = 0
    # end of critical section
    flag_0 = False


def p1():
    flag_1 = True
    turn = 0
    while flag_0 and turn == 0:
        pass  # busy wait
    turn = 1
    # critical section
    assert not cs_used
    cs_used = True
    cs_used = False
    # end of critical section
    flag_1 = False


# TODO: HALTS_ASSERT to do a better job
# proof([p0, p1], D, assertions=[HALTS_ASSERT])

proof([p0, p1], D)  # OK
