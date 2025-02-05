from bla.core import Assertion, FailedAssert, StateView


class NeverCyclesAssert(Assertion):
    def check(self, state: StateView, cyclic: bool) -> None:
        if cyclic:
            raise FailedAssert("There is a cycle in the program")


HALTS_ASSERT = NeverCyclesAssert()
