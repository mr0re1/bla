from typing import Callable
import ast, inspect
from core import Prog, Op, Label, Variables, ValuePredicate, eq, mov, cond

def _parse_val_predicate(expr: ast.expr, domain: type[Variables]) -> ValuePredicate:
    match expr:
        case ast.Compare(ast.Name(var), [ast.Eq()], [ast.Constant(val)]):
            assert var in domain.__members__, f"Unknown variable {var}"
            assert val in [True, False], f"Invalid value {val}"
            return eq(domain[var], val)
        case _:
            raise Exception("Expected comparison", ast)
                            

def _parse_op(t: ast.stmt, domain: type[Variables]) -> Op|Label:
    match t:
        case ast.Assign([ast.Name(var)], ast.Constant(val)):
            assert var in domain.__members__, f"Unknown variable {var}"
            assert val in [True, False], f"Invalid value {val}"
            return mov(domain[var], val)
        case ast.Assign():
            raise ValueError("Expected assignment format:\n\t var = constant")

        case ast.If(cmp,  [ast.Expr(ast.Constant(lbl))], orelse=[]) if isinstance(lbl, str):
            pred = _parse_val_predicate(cmp, domain)
            return cond(pred, lbl)
        case ast.If():
            raise ValueError('Expected "if" format:\n\t if var == const: "label"')
        
        case ast.Expr(ast.Constant(lbl)) if isinstance(lbl, str):
            return lbl
      
        case _:
            raise Exception("Unknown op", t)

def parse_program(f: Callable, domain: type[Variables]):
    src = inspect.getsource(f)
    t = ast.parse(src)
    match t.body:
        case [ast.FunctionDef(name, args, body)]:
            line_offset = t.body[0].lineno
            ops = []
            line_mapping = []
            for stmt in body:
                op = _parse_op(stmt, domain)
                ops.append(op)
                if not isinstance(op, Label):
                    line_mapping.append(stmt.lineno - line_offset)

        case _:
            raise Exception("Expected a single function, got", t.body)
    return PrettyProg(name, ops, src, line_mapping)


class PrettyProg(Prog):
    def __init__(self, name, ops, src, line_mapping):
        super().__init__(name, ops)
        self.src = src
        self.line_mapping = line_mapping
        print(self.line_mapping)
    
    def render(self, pos) -> Label:
        pos = self.line_mapping[pos] if pos < len(self.line_mapping) else None
        lines = self.src.split("\n")

        res = ""
        for i, line in enumerate(lines):
            if i == pos:
                res += f"->{line[2:]}\n"
            else:
                res += f"{line}\n"
        if pos == None: res += "==HALTED=="
        return res