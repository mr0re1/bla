from typing import Callable, Optional
from core import  Variables, Assertion, State, StateView
from tabulate import tabulate
from parse import parse_program

def proof(fns: list[Callable], domain: type[Variables], assertions: list[Assertion]=None) -> bool:
    if assertions is None:
        assertions = []
    progs = []
    for fn in fns:
        prog, asserts = parse_program(fn, domain)
        progs.append(prog)
        assertions += asserts

    state = State(
        pos=tuple([0] * len(progs)),
        val=tuple([False] * len(domain)))
    
    stack, visited = [state], {state: None}
    while stack:
        state = stack.pop()
        sv = StateView(state, progs)

        for a in assertions:
            try:
                a.check(sv)
            except Exception as e:
                explain(sv, domain, visited)
                print(f"Assertion failed: {e}")
                return False

        for ip, prog in enumerate(progs):
            pos = state.pos[ip]
            if pos >= len(prog.ops):
                continue
            npos, nv = prog.run(pos, state.val)
            nxt = State(
                pos=tuple(state.pos[:ip] + (npos,) + state.pos[ip+1:]), 
                val=nv)
            
            if nxt in visited: continue
            stack.append(nxt)
            visited[nxt] = state

    return True



def explain(sv: StateView, domain, parents):
    chain = []
    progs, state = sv.progs, sv.state
    while state is not None:
        chain.append(state)
        state = parents[state]
    
    for i, state in enumerate(reversed(chain)):
        print(f"----- step #{i}:")

        pgs = [progs[pi].render(pos) for pi, pos in enumerate(state.pos)]
        vls = "\n".join([f"{domain(i).name}={val}" for i, val in enumerate(state.val)])
        tbl = [pgs + [vls]]
        print(tabulate(tbl, tablefmt="presto"))
        print("\n")


