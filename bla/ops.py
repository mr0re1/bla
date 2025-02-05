from typing import Any

from bla.core import Variables, Op, ValuePredicate, Values, FailedAssert


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
        return (lbl, val) if pred(val) else (None, val)

    return impl


def goto(lbl: str) -> Op:
    def impl(val: Values):
        return lbl, val

    return impl


def assert_op(pred: ValuePredicate, msg: str):
    def impl(val: Values):
        if not pred(val):
            raise FailedAssert(msg)
        return None, val

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
