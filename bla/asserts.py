from bla.core import Assertion, FailedAssert, ValuePredicate, StateView, Values


class NeverCyclesAssert(Assertion):
    def check(self, state: StateView, cyclic: bool) -> None:
        if cyclic:
            raise FailedAssert("There is a cycle in the program")


HALTS_ASSERT = NeverCyclesAssert()


def assert_op(pred: ValuePredicate, msg: str):
    def impl(val: Values):
        if not pred(val):
            raise FailedAssert(msg)
        return None, val

    return impl
