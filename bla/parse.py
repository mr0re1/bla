from typing import Callable, Any
import ast, inspect
from dataclasses import dataclass, field

from bla import ops
from bla.memory import MemMap, Reference, Memory
from bla.core import Prog, Op, Label, Predicate, Sentinel


class BlaSyntaxError(SyntaxError):
    def __init__(self, msg: str, filename: str, lineno: int, offset: int, text: str):
        super().__init__(msg, (filename, lineno, offset, text))


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
    _end_lbl: Label = "__lbl_END"

    def ref(self, var: str) -> Reference:
        ref = Reference(var)
        self.mm.addr(ref)
        return ref

    def lineno(self, node: ast.stmt) -> int:
        return node.lineno - self.line_offset

    def uniq_label(self) -> str:
        self._nxt_label += 1
        return f"__lbl_{self._nxt_label}"

    def add_sentinel(self, sent: Sentinel | Label) -> None:
        self.stmts.append(sent)

    def add_op(self, op: Op, node: ast.stmt) -> None:
        assert callable(op)
        self.stmts.append(op)
        self.line_mapping.append(self.lineno(node))

    def syntax_err(self, msg: str, node: ast.stmt) -> BlaSyntaxError:
        lines = self.src.split("\n")
        lineno = self.lineno(node)
        text = lines[lineno] if 0 <= lineno < len(lines) else ast.unparse(node)

        return BlaSyntaxError(
            msg,
            # TODO: point at rela file & lineno
            filename=f"program:${self.prog_name}",
            lineno=lineno,
            offset=node.col_offset,
            text=text,
        )


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
    if len(t.targets) != 1:
        raise ctx.syntax_err("Tuple assignment is not supported", t)

    tgt = t.targets[0]
    # TODO: support atomic tuple-assignemt
    if not isinstance(tgt, ast.Name):
        raise ctx.syntax_err("Only assignment by name is supported", t)

    ref = ctx.ref(tgt.id)
    # TODO: use shorthand for `A = const` and `A = B`
    #  to avoid costly(?) expressions eval
    expr = ops.EvalExpr.from_ast(t.value, ctx.mm)
    ctx.add_op(ops.mov(ctx.mm, ref, expr), t)


def _parse_if(t: ast.If, ctx: _ParseCtx):
    # There are two cases:
    # `if: ...` - requires one label (else == end) and one cond-goto
    # `if: ... else: ...` - requires two labels (else != end), one cond-goto, and one goto

    else_lbl = ctx.uniq_label()
    pred = _parse_predicate(t.test, ctx)
    if_op = ops.cond(pred, else_lbl, negate=True)

    ctx.add_op(if_op, t)
    _parse_body(t.body, ctx)

    if t.orelse:  # if: ... else: ...
        end_lbl = ctx.uniq_label()
        ctx.add_op(ops.goto(end_lbl), t.body[-1])

        ctx.add_sentinel(else_lbl)
        _parse_body(t.orelse, ctx)

    else:  # if: ...
        end_lbl = else_lbl

    ctx.add_sentinel(end_lbl)


def _parse_while(t: ast.While, ctx: _ParseCtx):
    if t.orelse:
        raise ctx.syntax_err("else-clause in while-loop is not supported", t.orelse[0])

    pred = _parse_predicate(t.test, ctx)

    begin_lbl = ctx.uniq_label()
    end_lbl = ctx.uniq_label()

    ctx.add_sentinel(begin_lbl)
    ctx.add_op(ops.cond(pred, end_lbl, negate=True), t)

    ctx._continue_lbls.append(begin_lbl)
    ctx._break_lbls.append(end_lbl)

    _parse_body(t.body, ctx)
    ctx.add_op(ops.goto(begin_lbl), t)
    ctx.add_sentinel(end_lbl)

    ctx._break_lbls.pop()
    ctx._continue_lbls.pop()


def _parse_with(t: ast.With, ctx: _ParseCtx):
    if len(t.items) != 1:
        raise ctx.syntax_err("Only one item is supported", t)

    it = t.items[0]

    if it.optional_vars:
        raise ctx.syntax_err("Optional vars are not supported", t)

    match it.context_expr:
        case ast.Name("atomic"):
            _parse_atomic_context(t.body, ctx)
        case _:
            raise ctx.syntax_err("Unsupported context, only 'atomic' is supported", t)


def _parse_atomic_context(body: list[ast.stmt], ctx: _ParseCtx):
    if ctx._atomic_context:
        raise ctx.syntax_err("Nested atomic context is not supported", body[0])
        # TODO: use better anchor than body[0]

    ctx._atomic_context = True
    ctx.add_sentinel(Sentinel.ATOMIC_ENTER)
    _parse_body(body, ctx)
    ctx.add_sentinel(Sentinel.ATOMIC_EXIT)
    ctx._atomic_context = False


def _parse_assert(t: ast.Assert, ctx: _ParseCtx):
    msg = ast.unparse(t)
    pred = _parse_predicate(t.test, ctx)
    ctx.add_op(ops.assert_op(pred, msg=msg), t)


def _parse_break(t: ast.Break, ctx: _ParseCtx):
    if not ctx._break_lbls:
        raise ctx.syntax_err("'break' outside loop", t)
    ctx.add_op(ops.goto(ctx._break_lbls[-1]), t)


def _parse_continue(t: ast.Continue, ctx: _ParseCtx):
    if not ctx._continue_lbls:
        raise ctx.syntax_err("'continue' outside loop", t)
    ctx.add_op(ops.goto(ctx._continue_lbls[-1]), t)


def _parse_return(t: ast.Return, ctx: _ParseCtx):
    if t.value:
        raise ctx.syntax_err("'return' can not be used with value", t)
    ctx.add_op(ops.goto(ctx._end_lbl), t)


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
        case ast.Return():
            _parse_return(t, ctx)

        case _:
            raise ctx.syntax_err("Unknown op", t)


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
            ctx.add_sentinel(ctx._end_lbl)

        case _:
            raise Exception("Expected a single function, got", t.body)
    return PrettyProg(ctx)


class PrettyProg(Prog):
    def __init__(self, ctx: _ParseCtx):
        super().__init__(ctx.prog_name, ctx.stmts)
        self.ctx = ctx
        self.lines = ctx.src.split("\n")

    def render_op(self, pos) -> str:
        ln = self.ctx.line_mapping[pos] if pos < len(self.ctx.line_mapping) else None
        if ln is None:
            return "<HALTED>"

        return self.lines[ln]
