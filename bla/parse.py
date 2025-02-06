from typing import Callable, Any
import ast, inspect
from dataclasses import dataclass, field

from bla import ops
from bla.memory import MemMap, Reference, Memory
from bla.core import Prog, Op, Label, Predicate, Sentinel


@dataclass
class _ParseCtx:
    prog_name: str
    src: str
    mm: MemMap
    line_offset: int
    stmts: list[Op | Label | Sentinel] = field(default_factory=list)
    line_mapping: list[int] = field(
        default_factory=list
    )  # maps from state.pos to src line
    _nxt_label: int = 0
    _atomic_context: bool = False

    _break_lbls: list[Label] = field(default_factory=list)
    _continue_lbls: list[Label] = field(default_factory=list)

    def ref(self, var: str) -> Reference:
        ref = Reference(var)
        self.mm.addr(ref)
        return ref

    def lineno(self, node: ast.stmt) -> int:
        return node.lineno - self.line_offset

    def uniq_label(self) -> str:
        self._nxt_label += 1
        return f"__lbl_{self._nxt_label}"

    def add_stmt(self, stmt: Op | Label | Sentinel, node: ast.stmt) -> None:
        match stmt:
            case Label() | Sentinel():
                self.stmts.append(stmt)  # Go to program but not getting line mapping
                # TODO: don't leak this detail of Prog impplelemtation
            case _ as op:
                assert callable(op)
                self.stmts.append(op)
                self.line_mapping.append(self.lineno(node))


def _parse_predicate(t: ast.expr, ctx: _ParseCtx) -> Predicate:
    # TODO: use shorthand for `const` and `A`
    #  to avoid costly(?) expressions eval
    expr = ops.EvalExpr.from_ast(t, ctx.mm)

    def pred(mem: Memory) -> bool:  # TODO: move somewhere
        val = expr(mem)
        assert isinstance(val, bool)
        return val

    return pred


def _parse_assign(t: ast.Assign, ctx: _ParseCtx):
    assert len(t.targets) == 1, "Tuple assignment is not supported"
    tgt = t.targets[0]
    assert isinstance(tgt, ast.Name), "Only assignment by name is supported"

    ref = ctx.ref(tgt.id)
    # TODO: use shorthand for `A = const` and `A = B`
    #  to avoid costly(?) expressions eval
    expr = ops.EvalExpr.from_ast(t.value, ctx.mm)
    ctx.add_stmt(ops.mov(ctx.mm, ref, expr), t)


def _parse_if(t: ast.If, ctx: _ParseCtx):
    # There are two cases:
    # `if: ...` - requires one label (else == end) and one cond-goto
    # `if: ... else: ...` - requires two labels (else != end), one cond-goto, and one goto

    else_lbl = ctx.uniq_label()
    pred = _parse_predicate(t.test, ctx)
    if_op = ops.cond(ops.negate(pred), else_lbl)

    ctx.add_stmt(if_op, t)
    _parse_body(t.body, ctx)

    if t.orelse:  # if: ... else: ...
        end_lbl = ctx.uniq_label()
        ctx.add_stmt(ops.goto(end_lbl), t.body[-1])

        ctx.add_stmt(else_lbl, t.orelse[0])
        _parse_body(t.orelse, ctx)

    else:  # if: ...
        end_lbl = else_lbl

    ctx.add_stmt(end_lbl, t)


def _parse_while(t: ast.While, ctx: _ParseCtx):
    assert not t.orelse, "else-clause in while-loop is not supported"

    pred = _parse_predicate(t.test, ctx)

    begin_lbl = ctx.uniq_label()
    end_lbl = ctx.uniq_label()

    ctx.add_stmt(begin_lbl, t)
    ctx.add_stmt(ops.cond(ops.negate(pred), end_lbl), t)

    ctx._continue_lbls.append(begin_lbl)
    ctx._break_lbls.append(end_lbl)

    _parse_body(t.body, ctx)
    ctx.add_stmt(ops.goto(begin_lbl), t)
    ctx.add_stmt(end_lbl, t)

    ctx._break_lbls.pop()
    ctx._continue_lbls.pop()


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
    msg = ast.unparse(t)
    pred = _parse_predicate(t.test, ctx)
    ctx.add_stmt(ops.assert_op(pred, msg=msg), t)


def _parse_break(t: ast.Break, ctx: _ParseCtx):
    assert ctx._break_lbls, "brake outside of a loop"
    ctx.add_stmt(ops.goto(ctx._break_lbls[-1]), t)


def _parse_continue(t: ast.Continue, ctx: _ParseCtx):
    assert ctx._continue_lbls, "continue outside of a loop"
    ctx.add_stmt(ops.goto(ctx._continue_lbls[-1]), t)


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
        case ast.Break():
            _parse_break(t, ctx)
        case ast.Continue():
            _parse_continue(t, ctx)

        case _:
            raise Exception("Unknown op", ast.unparse(t))


def _parse_body(body: list[ast.stmt], ctx: _ParseCtx):
    for stmt in body:
        _parse_stmt(stmt, ctx)


def _check_empty_args(args: ast.arguments) -> None:
    if args.args or args.vararg or args.kwarg:
        raise Exception(f"Expected no arguments, got {args.__dict__}")


def parse_program(f: Callable, mm: MemMap) -> Prog:
    src = inspect.getsource(f)
    t = ast.parse(src)
    match t.body:
        case [ast.FunctionDef(name, args, body)]:
            _check_empty_args(args)
            ctx = _ParseCtx(
                prog_name=name,
                src=src,
                mm=mm,
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
