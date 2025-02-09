from enum import Enum
from typing import Callable, Protocol, Any
from dataclasses import dataclass
from bla.memory import Memory


@dataclass(frozen=True)
class State:
    pos: tuple[int, ...]
    val: Memory


Label = str
Op = Callable[[Memory], tuple[Label | None, Memory]]
Expr = Callable[[Memory], Any]
Predicate = Callable[[Memory], bool]


class FailedAssert(Exception):
    pass


class Sentinel(Enum):
    ATOMIC_ENTER = object()
    ATOMIC_EXIT = object()

    def __repr__(self):
        return f"<{self.name}>"


class Prog:
    def __init__(self, name, stmts: list[Op | Label | Sentinel]):
        self.name = name
        self.labels: dict[str, int] = {}
        self.ops: list[Op] = []
        self.atomic: list[bool] = []

        in_atomic_ctx = False

        for stmt in stmts:
            match stmt:
                case Label() as lbl:
                    self.labels[lbl] = len(self.ops)

                case Sentinel.ATOMIC_ENTER | Sentinel.ATOMIC_EXIT as sentinel:
                    nxt = sentinel is Sentinel.ATOMIC_ENTER
                    assert nxt != in_atomic_ctx
                    in_atomic_ctx = nxt

                case _ as op:
                    assert callable(op)
                    self.ops.append(op)
                    self.atomic.append(in_atomic_ctx)

    def run(self, pos: int, vals: Memory) -> tuple[int, Memory, bool]:
        assert 0 <= pos < len(self.ops)
        lbl, vals = self.ops[pos](vals)

        if lbl is not None:
            assert lbl in self.labels, f"Label {lbl} not found"
            nxt_pos = self.labels[lbl]
        else:
            nxt_pos = pos + 1

        atomic = nxt_pos < len(self.ops) and self.atomic[nxt_pos] and self.atomic[pos]

        return nxt_pos, vals, atomic

    def render(self, pos) -> str:
        res = f"def {self.name}"
        for i, op in enumerate(self.ops):
            pref = "  " if i != pos else "->"
            res += f"\n{pref}{op}"
        return res
