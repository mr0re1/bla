from typing import Callable
import ast, inspect
from core import Prog, Op, Label, Variables, ValuePredicate, eq, mov, cond
from dataclasses import dataclass

@dataclass
class _ParseCtx:
    prog_name: str
    src: str
    domain: type[Variables]
    line_offset: int
    ops: list[Op|Label]
    line_mapping: list[int] # maps from state.pos to src line

    def check_var(self, var: str):
        assert var in self.domain.__members__, f"Unknown variable {var}"

    def check_var_val(self, var: str, val: any):
        self.check_var(var)
        assert val in [True, False], f"Invalid value {val} for {var}"

    def var(self, name: str) -> Variables:
        self.check_var(name)
        return self.domain[name]
    
    def lineno(self, node: ast.AST) -> int:
        return node.lineno - self.line_offset
    
    def add_op(self, op: Op|Label, stmt: ast.AST) -> None:
        self.ops.append(op)
        if not isinstance(op, Label):
            self.line_mapping.append(self.lineno(stmt))


def _parse_val_predicate(expr: ast.expr, ctx: _ParseCtx) -> ValuePredicate:
    match expr:
        case ast.Compare(ast.Name(var), [ast.Eq()], [ast.Constant(val)]):
            ctx.check_var_val(var, val)
            return eq(ctx.var(var), val)
        case _:
            raise Exception("Expected comparison", ast)
                            

def _parse_op(t: ast.stmt, ctx: _ParseCtx) -> Op|Label:
    match t:
        case ast.Assign([ast.Name(var)], ast.Constant(val)):
            ctx.check_var_val(var, val)
            return mov(ctx.var(var), val)
        case ast.Assign():
            raise ValueError("Expected assignment format:\n\t var = constant")

        case ast.If(cmp,  [ast.Expr(ast.Constant(lbl))], orelse=[]) if isinstance(lbl, str):
            pred = _parse_val_predicate(cmp, ctx)
            return cond(pred, lbl)
        case ast.If():
            raise ValueError('Expected "if" format:\n\t if var == const: "label"')
        
        case ast.Expr(ast.Constant(lbl)) if isinstance(lbl, str):
            return lbl
        
        case ast.Assert(tst, msg):
            pred = _parse_val_predicate(tst, ctx)
            raise ValueError("Assert not supported", t)
      
        case _:
            raise Exception("Unknown op", t)

def parse_program(f: Callable, domain: type[Variables]):
    src = inspect.getsource(f)
    t = ast.parse(src)
    match t.body:
        case [ast.FunctionDef(name, args, body)]:
            ctx = _ParseCtx(
                prog_name=name, src=src, domain=domain, line_offset=t.body[0].lineno, ops=[], line_mapping=[])
            for stmt in body:
                op = _parse_op(stmt, ctx)
                ctx.add_op(op, stmt)

        case _:
            raise Exception("Expected a single function, got", t.body)
    return PrettyProg(ctx)


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