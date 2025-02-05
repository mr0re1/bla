from enum import IntEnum, Enum
from typing import Callable, Any
from dataclasses import dataclass


class Variables(IntEnum):
    def _generate_next_value_(name, start, count, last_values):
        return count


Values = tuple[bool, ...]


@dataclass(frozen=True)
class State:
    pos: tuple[int, ...]
    val: Values


@dataclass(frozen=True)
class StateView:
    state: State
    progs: list["Prog"]

    def prog_idx(self, name) -> int:
        for i, p in enumerate(self.progs):
            if p.name == name:
                return i
        raise KeyError(f"Program {name} not found")

    def pos(self, name) -> int:
        pi = self.prog_idx(name)
        return self.state.pos[pi]

    def val(self, var: Variables) -> bool:
        return self.state.val[var]


Label = str
Op = Callable[[Values], tuple[Label | None, Values]]
ValuePredicate = Callable[[Values], bool]


class Assertion:
    def check(self, state: StateView, cyclic: bool) -> None:
        raise NotImplementedError()


class FailedAssert(Exception):
    pass


def mov(var: Variables, value: Any) -> Op:
    def impl(mem: Values):
        val = value  # to satisfy "match"
        match val:
            case Variables():  # A = B
                val = mem[val]
            case _:  # A = True
                pass

        nv = list(mem)
        nv[var] = val
        return None, tuple(nv)

    return impl


def cond(pred: ValuePredicate, lbl: str) -> Op:
    def impl(val: Values):
        return lbl if pred(val) else None, val

    return impl


def goto(lbl: str) -> Op:
    def impl(val: Values):
        return lbl, val

    return impl


def eq(var: Variables, value: Any) -> ValuePredicate:
    def impl(mem: Values) -> bool:
        val = value  # to satisfy "match"
        match val:
            case Variables():
                val = mem[value]
        return mem[var] == value

    return impl


def const(val: bool) -> ValuePredicate:
    return lambda _: val


def negate(pred: ValuePredicate) -> ValuePredicate:
    return lambda val: not pred(val)


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

    def run(self, pos: int, vals: Values) -> tuple[int, Values, bool]:
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
