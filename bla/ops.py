from typing import Any

from bla.memory import Reference, MemMap, Memory
from bla.core import Op, ValuePredicate, FailedAssert


def _assign_mem(mem: Memory, addr: int, value: Any) -> Memory:
    nv = list(mem)
    nv[addr] = value
    return tuple(nv)


def mov(mm: MemMap, var: Reference, value: Any | Reference) -> Op:
    daddr = mm.addr(var)
    if isinstance(value, Reference):
        saddr = mm.addr(value)
        # TODO: check type match

        def impl(mem: Memory):
            return None, _assign_mem(mem, daddr, mem[saddr])

    else:
        mm.validate(var, value)

        def impl(mem: Memory):
            return None, _assign_mem(mem, daddr, value)

    return impl


def cond(pred: ValuePredicate, lbl: str) -> Op:
    def impl(val: Memory):
        return (lbl, val) if pred(val) else (None, val)

    return impl


def goto(lbl: str) -> Op:
    def impl(val: Memory):
        return lbl, val

    return impl


def assert_op(pred: ValuePredicate, msg: str):
    def impl(val: Memory):
        if not pred(val):
            raise FailedAssert(msg)
        return None, val

    return impl


def eq(mm: MemMap, var: Reference, value: Any | Reference) -> ValuePredicate:
    addr = mm.addr(var)

    if isinstance(value, Reference):
        caddr = mm.addr(value)
        # TODO: check type match
        def impl(mem: Memory) -> bool:
            return mem[addr] == mem[caddr]

    else:
        mm.validate(var, value)

        def impl(mem: Memory) -> bool:
            return mem[addr] == value

    return impl


def const(val: bool) -> ValuePredicate:
    return lambda _: val


def negate(pred: ValuePredicate) -> ValuePredicate:
    return lambda val: not pred(val)
