from typing import Callable
import ast, inspect
from dataclasses import dataclass

from bla.core import Prog, Op, Label, Variables, ValuePredicate, eq, const, mov, cond, Assertion
from bla.asserts import PosAssert


@dataclass
class _ParseCtx:
    prog_name: str
    src: str
    domain: type[Variables]
    line_offset: int
    ops: list[Op|Label]
    line_mapping: list[int] # maps from state.pos to src line
    asserts: list[Assertion]

    def check_var(self, var: str) -> Variables:
        assert var in self.domain.__members__, f"Unknown variable {var}"
        return self.domain[var]

    def check_var_val(self, var: str, val: any):
        self.check_var(var)
        assert val in [True, False], f"Invalid value {val} for {var}"

    def var(self, name: str) -> Variables:
        return self.check_var(name)
    
    def lineno(self, node: ast.AST) -> int:
        return node.lineno - self.line_offset
    
    def add_op(self, op: Op|Label, stmt: ast.AST) -> None:
        match op:
            case Label():
                self.ops.append(op) # labels also added to ops
            case Assertion():
                self.asserts.append(op)
            case _: # Op; TODO: better check
                self.ops.append(op)
                self.line_mapping.append(self.lineno(stmt))


def _parse_val_predicate(expr: ast.expr, ctx: _ParseCtx) -> ValuePredicate:
    match expr:
        case ast.Compare(ast.Name(var), [ast.Eq()], [ast.Constant(val)]):
            ctx.check_var_val(var, val)
            return eq(ctx.var(var), val)
        case ast.Compare(ast.Name(var), [ast.Eq()], [ast.Name(val)]):
            return eq(ctx.check_var(var), ctx.check_var(val))
        case ast.Constant(val):
            assert val in [True, False], f"Invalid value {val}"
            return const(val)
        case _:
            raise Exception("Expected comparison, got", ast.unparse(expr))
                            

def _parse_op(t: ast.stmt, ctx: _ParseCtx) -> Op|Label|Assertion:
    match t:
        case ast.Assign([ast.Name(var)], ast.Constant(val)):
            ctx.check_var_val(var, val)
            return mov(ctx.var(var), val)
        case ast.Assign([ast.Name(var)], ast.Name(val)):
            return mov(ctx.check_var(var), ctx.check_var(val))
        case ast.Assign():
            raise ValueError("Expected assignment format:\n\t var = constant | var")

        case ast.If(cmp,  [ast.Expr(ast.Constant(lbl))], orelse=[]) if isinstance(lbl, str):
            pred = _parse_val_predicate(cmp, ctx)
            return cond(pred, lbl)
        case ast.If():
            raise ValueError('Expected "if" format:\n\t if var == const: "label"')
        
        case ast.Expr(ast.Constant(lbl)) if isinstance(lbl, str):
            return lbl
        
        case ast.Assert(tst):
            pred = _parse_val_predicate(tst, ctx)
            return PosAssert(pred, ctx.prog_name, len(ctx.line_mapping), msg=ast.unparse(t))
      
        case _:
            raise Exception("Unknown op", t)

def _check_empty_args(args: ast.arguments) -> None:
    if args.args or args.vararg or args.kwarg:
        raise Exception(f"Expected no arguments, got {args.__dict__}")

def parse_program(f: Callable, domain: type[Variables]) -> tuple[Prog, list[Assertion]]:
    src = inspect.getsource(f)
    t = ast.parse(src)
    match t.body:
        case [ast.FunctionDef(name, args, body)]:
            _check_empty_args(args)
            ctx = _ParseCtx(
                prog_name=name, src=src, domain=domain, line_offset=t.body[0].lineno, 
                # TODO: use default vals
                ops=[], line_mapping=[], asserts=[])
            for stmt in body:
                op = _parse_op(stmt, ctx)
                ctx.add_op(op, stmt)

        case _:
            raise Exception("Expected a single function, got", t.body)
    return PrettyProg(ctx), ctx.asserts


class PrettyProg(Prog):
    def __init__(self, ctx: _ParseCtx):
        super().__init__(ctx.prog_name, ctx.ops)
        self.ctx = ctx
    
    def render(self, pos) -> Label:
        pos = self.ctx.line_mapping[pos] if pos < len(self.ctx.line_mapping) else None
        lines = self.ctx.src.split("\n")

        res = ""
        for i, line in enumerate(lines):
            if i == pos:
                res += f"->{line[2:]}\n"
            else:
                if i + 1 == len(lines) and not line: continue # skip last empty line
                res += f"{line}\n"
        if pos == None: res += "->==HALTED=="
        return res