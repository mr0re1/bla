from enum import IntEnum
from typing import Callable
from dataclasses import dataclass

class Variables(IntEnum):
    def _generate_next_value_(name, start, count, last_values): return count


Values = tuple[bool]

@dataclass(frozen=True)
class State:
    pos: tuple[int]
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
Op = Callable[[Values], tuple[Label|None, Values]]
ValuePredicate = Callable[[Values], bool]

class Assertion:
    def check(self, state: StateView) -> None:
        raise NotImplementedError

class FailedAssert(Exception):
    pass

def mov(var: Variables, value: any) -> Op:
    def impl(mem: Values):
        val = value # to satisfy "match"
        match val:
            case Variables(): # A = B
                val = mem[val]
            case _: # A = True
                pass
        
        nv = list(mem)
        nv[var] = val
        return None, tuple(nv)
    
    return impl

def cond(pred: ValuePredicate, lbl: str) -> Op:
    def impl(val: Values):
        return lbl if pred(val) else None, val
    return impl

def eq(var: Variables, value: any) -> ValuePredicate:
    def impl(mem: Values) -> bool:
        val = value # to satisfy "match"
        match val:
            case Variables():
                val = mem[value]
        return mem[var] == value
    return impl

def const(val: bool) -> ValuePredicate:
    return lambda _: val

class Prog:
    def __init__(self, name, ops: list[Op | Label]):
        self.name = name
        self.labels: dict[str, int] = {}
        self.ops = []

        for op in ops:
            if isinstance(op, Label):
                self.labels[op] = len(self.ops)
            else:
                self.ops.append(op)
    
    def run(self, pos: int, vals: Values) -> tuple[int, Values]:
        assert 0 <= pos < len(self.ops)
        lbl, vals = self.ops[pos](vals)
        
        if lbl is not None:
            assert lbl in self.labels, f"Label {lbl} not found"
            pos = self.labels[lbl]
        else: pos = pos + 1

        return pos, vals
    
    def render(self, pos) -> str:
        res = f"def {self.name}"
        for i, op in enumerate(self.ops):
            pref = "  " if i != pos else "->"
            res += f"\n{pref}{op}"
        return res

