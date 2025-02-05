from typing import Callable, Any
import ast, inspect
from dataclasses import dataclass, field

from bla import ops
from bla.core import Prog, Op, Label, Variables, ValuePredicate, Sentinel


@dataclass
class _ParseCtx:
    prog_name: str
    src: str
    domain: type[Variables]
    line_offset: int
    stmts: list[Op | Label] = field(default_factory=list)
    line_mapping: list[int] = field(
        default_factory=list
    )  # maps from state.pos to src line
    _nxt_label: int = 0
    _atomic_context: bool = False

    def check_var(self, var: str) -> Variables:
        assert var in self.domain.__members__, f"Unknown variable {var}"
        return self.domain[var]

    def check_var_val(self, var: str, val: Any):
        self.check_var(var)
        assert val in [True, False], f"Invalid value {val} for {var}"

    def var(self, name: str) -> Variables:
        return self.check_var(name)

    def lineno(self, node: ast.AST) -> int:
        return node.lineno - self.line_offset

    def uniq_label(self) -> str:
        self._nxt_label += 1
        return f"__lbl_{self._nxt_label}"

    def add_stmt(self, stmt: Op | Label | Sentinel, node: ast.AST) -> None:
        match stmt:
            case Label() | Sentinel():
                self.stmts.append(stmt)  # Go to program but not getting line mapping
                # TODO: don't leak this detail of Prog impplelemtation
            case _ as op:
                assert callable(op)
                self.stmts.append(op)
                self.line_mapping.append(self.lineno(node))


def _parse_val_predicate(expr: ast.expr, ctx: _ParseCtx) -> ValuePredicate:
    match expr:
        case ast.Compare(ast.Name(var), [ast.Eq()], [ast.Constant(val)]):
            ctx.check_var_val(var, val)
            return ops.eq(ctx.var(var), val)
        case ast.Compare(ast.Name(var), [ast.Eq()], [ast.Name(val)]):
            return ops.eq(ctx.check_var(var), ctx.check_var(val))
        case ast.Constant(val):
            assert val in [True, False], f"Invalid value {val}"
            return ops.const(val)
        case ast.Name(var):
            return ops.eq(ctx.check_var(var), True)
        case _:
            raise Exception("Expected comparison, got", ast.unparse(expr))


def _parse_assign(t: ast.Assign, ctx: _ParseCtx):
    match t:
        case ast.Assign([ast.Name(var)], ast.Constant(val)):
            ctx.check_var_val(var, val)
            ctx.add_stmt(ops.mov(ctx.var(var), val), t)
        case ast.Assign([ast.Name(var)], ast.Name(val)):
            ctx.add_stmt(ops.mov(ctx.check_var(var), ctx.check_var(val)), t)
        case _:
            raise ValueError("Expected assignment format:\n\t var = constant | var")


def _parse_if(t: ast.If, ctx: _ParseCtx):
    if t.orelse:
        raise NotImplementedError("Else clause is not supported yet")

    pred = _parse_val_predicate(t.test, ctx)
    else_lbl = ctx.uniq_label()
    if_op = ops.cond(ops.negate(pred), else_lbl)

    ctx.add_stmt(if_op, t)
    _parse_body(t.body, ctx)
    ctx.add_stmt(else_lbl, t)


def _parse_while(t: ast.While, ctx: _ParseCtx):
    if t.orelse:
        raise NotImplementedError("Else clause is not supported yet")

    pred = _parse_val_predicate(t.test, ctx)
    begin_lbl = ctx.uniq_label()
    end_lbl = ctx.uniq_label()

    ctx.add_stmt(begin_lbl, t)
    ctx.add_stmt(ops.cond(ops.negate(pred), end_lbl), t)
    _parse_body(t.body, ctx)
    ctx.add_stmt(ops.goto(begin_lbl), t)
    ctx.add_stmt(end_lbl, t)


def _parse_with(t: ast.With, ctx: _ParseCtx):
    assert t.type_comment is None, "Type comments are not supported"
    assert len(t.items) == 1, "Only one item is supported"
    it = t.items[0]
    assert it.optional_vars is None, "Optional vars are not supported"
    match it.context_expr:
        case ast.Name("atomic"):
            _parse_atomic_context(t.body, ctx)
        case _:
            raise Exception("Unsupported context, only 'atomic' is supported")


def _parse_atomic_context(body: list[ast.stmt], ctx: _ParseCtx):
    assert not ctx._atomic_context, "Nested atomic context is not supported"

    ctx._atomic_context = True
    ctx.add_stmt(Sentinel.ATOMIC_ENTER, body[0])
    _parse_body(body, ctx)
    ctx.add_stmt(Sentinel.ATOMIC_EXIT, body[0])
    ctx._atomic_context = False


def _parse_assert(t: ast.Assert, ctx: _ParseCtx):
    pred = _parse_val_predicate(t.test, ctx)
    ctx.add_stmt(ops.assert_op(pred, msg=ast.unparse(t)), t)


def _parse_stmt(t: ast.stmt, ctx: _ParseCtx):
    match t:
        case ast.Assert():
            _parse_assert(t, ctx)
        case ast.Assign():
            _parse_assign(t, ctx)
        case ast.If():
            _parse_if(t, ctx)
        case ast.While():
            _parse_while(t, ctx)
        case ast.With():
            _parse_with(t, ctx)
        case ast.Pass():
            pass  # don't add anything to prog

        case _:
            raise Exception("Unknown op", ast.unparse(t))


def _parse_body(body: list[ast.stmt], ctx: _ParseCtx):
    for stmt in body:
        _parse_stmt(stmt, ctx)


def _check_empty_args(args: ast.arguments) -> None:
    if args.args or args.vararg or args.kwarg:
        raise Exception(f"Expected no arguments, got {args.__dict__}")


def parse_program(f: Callable, domain: type[Variables]) -> Prog:
    src = inspect.getsource(f)
    t = ast.parse(src)
    match t.body:
        case [ast.FunctionDef(name, args, body)]:
            _check_empty_args(args)
            ctx = _ParseCtx(
                prog_name=name,
                src=src,
                domain=domain,
                line_offset=t.body[0].lineno,
            )
            _parse_body(body, ctx)

        case _:
            raise Exception("Expected a single function, got", t.body)
    return PrettyProg(ctx)


class PrettyProg(Prog):
    def __init__(self, ctx: _ParseCtx):
        super().__init__(ctx.prog_name, ctx.stmts)
        self.ctx = ctx

    def render(self, pos) -> Label:
        pos = self.ctx.line_mapping[pos] if pos < len(self.ctx.line_mapping) else None
        lines = self.ctx.src.split("\n")

        res = ""
        for i, line in enumerate(lines):
            if i == pos:
                res += f"->{line[2:]}\n"
            else:
                if i + 1 == len(lines) and not line:
                    continue  # skip last empty line
                res += f"{line}\n"
        if pos == None:
            res += "->==HALTED=="
        return res
