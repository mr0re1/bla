from dataclasses import dataclass

from bla.core import Assertion, FailedAssert, ValuePredicate, StateView


@dataclass(frozen=True)
class PosAssert(Assertion):
    """
    Assertion that is only checked in particular position of the program
    - i.e. normal assert behavior.
    """

    pred: ValuePredicate
    prog_name: str
    pos: int
    msg: str

    def check(self, state: StateView, cyclic: bool) -> None:
        if state.pos(self.prog_name) != self.pos:
            return
        if not self.pred(state.state.val):
            raise FailedAssert(f"{self.prog_name}:{self.pos}: {self.msg}")


class NeverCyclesAssert(Assertion):
    def check(self, state: StateView, cyclic: bool) -> None:
        if cyclic:
            raise FailedAssert("There is a cycle in the program")


HALTS_ASSERT = NeverCyclesAssert()
