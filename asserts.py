from typing import Callable
from core import Assertion, ValuePredicate, State, StateView

class BaseAssertion(Assertion):
    def __init__(self, fn: Callable[[StateView], None]):
        self.fn = fn

    def check(self, state: StateView) -> None:
        self.fn(state)


class PosAssert(Assertion):
    def __init__(self, pred: ValuePredicate, prog_name: str, pos: int, msg: str):
        self.pred = pred
        self.prog_name = prog_name
        self.pos = pos
        self.msg = msg

    def check(self, state: StateView) -> None:
        if state.pos(self.prog_name) != self.pos:
            return
        if not self.pred(state.state.val):
             raise Exception(f"{self.prog_name}:{self.pos}: {self.msg}")