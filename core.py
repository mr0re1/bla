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

Label = str
Op = Callable[[Values], tuple[Label|None, Values]]
ValuePredicate = Callable[[Values], bool]
Assertion = Callable[[State], bool]



def mov(var: Variables, value: any) -> Op:
    def impl(val: Values):
        nv = list(val)
        nv[var] = value
        return None, tuple(nv)
    return impl

def cond(pred: ValuePredicate, lbl: str) -> Op:
    def impl(val: Values):
        return lbl if pred(val) else None, val
    return impl

def eq(var: Variables, value: any) -> ValuePredicate:
    return lambda val: val[var] == value

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

