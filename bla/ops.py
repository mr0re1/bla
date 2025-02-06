from typing import Any
from types import CodeType
import ast

from bla.memory import Reference, MemMap, Memory
from bla.core import Op, Predicate, FailedAssert, Expr


def _assign_mem(mem: Memory, addr: int, value: Any) -> Memory:
    nv = list(mem)
    nv[addr] = value
    return tuple(nv)


def mov(mm: MemMap, var: Reference, expr: Expr) -> Op:
    daddr = mm.addr(var)

    def impl(mem: Memory):
        val = expr(mem)
        try:
            mm.validate(var, val)
        except AssertionError as e:  # TODO: don't rethrow, make MM to throw correct type
            raise FailedAssert(str(e))
        return None, _assign_mem(mem, daddr, expr(mem))

    return impl


def cond(pred: Predicate, lbl: str, negate: bool) -> Op:
    dst = (lbl, None) if negate else (None, lbl)

    def impl(val: Memory):
        return (dst[pred(val)], val)

    return impl


def goto(lbl: str) -> Op:
    def impl(val: Memory):
        return lbl, val

    return impl


def assert_op(pred: Predicate, msg: str):
    def impl(val: Memory):
        if not pred(val):
            raise FailedAssert(msg)
        return None, val

    return impl


class DereferencerNodeTransformer(ast.NodeTransformer):
    def __init__(self, mm: MemMap, mem_var: str):
        self._mm = mm
        self._mem_var = mem_var

    def visit_Name(self, node: ast.Name) -> ast.expr:
        addr = self._mm.addr(Reference(node.id))
        return ast.Subscript(
            value=ast.Name(id=self._mem_var, ctx=ast.Load()),
            slice=ast.Constant(value=addr),
            ctx=node.ctx,
        )


class EvalExpr:
    def __init__(self, code: CodeType):
        self._code = code

    def __call__(self, m: Memory) -> Any:
        m = m
        return eval(self._code)

    @classmethod
    def from_ast(cls, t: ast.expr, mm: MemMap) -> "EvalExpr":
        deref: ast.Expr = DereferencerNodeTransformer(mm, "m").visit(t)
        # Doing naive "compile from string" to avoid complex/wrong positioning
        # filling (lineno etc) in DereferencerNodeTransformer
        # If it proves to be requires (e.g. better error rendering),
        # fix DereferencerNodeTransformer and use
        # >> expression = ast.Expression(deref)
        # >> code = compile(expression, filename="<bla>", mode="eval")
        code = compile(ast.unparse(deref), filename="<bla>", mode="eval")
        return cls(code=code)
