import sys

sys.path.insert(0, "../bla")

from bla import proof


def setter_checker_non_atomic():
    A = True
    assert A == True


def setter_checker_atomic():
    with atomic:
        A = True
        assert A == True
        A = False  # Can be removed once positional assert are fixed


def corrupter():
    A = False


D = {"A": bool}

print("*** Expected failure:")
proof([setter_checker_non_atomic, corrupter], D)

print("*** Passes")
proof([setter_checker_atomic, corrupter], D)
