from core import  Variables
from parse import parse_program
from proof import proof

V = Variables("Vars", [ "A"])

def pA():
    A = True
    if A == True: "fin"
    A = False
    "fin"
    # assert A == True

def pB():
    A = False
    A = True

prog_a = parse_program(pA, V)
prog_b = parse_program(pB, V)


proof([prog_a, prog_b], V, [
   lambda s: s.val[V.A] == True if s.pos[0] == 3 else True,
])


    



