from core import Prog, Variables, Assertion, State
from tabulate import tabulate

def proof(progs: list[Prog], domain: type[Variables], assertions: list[Assertion]) -> bool:
    state = State(
        pos=tuple([0] * len(progs)),
        val=tuple([False] * len(domain)))
    
    stack, visited = [state], {state: None}
    while stack:
        state = stack.pop()

        for a in assertions:
            if not a(state):
                explain(progs, domain, state, visited)
                print(f"Assertion failed: {a}")
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



def explain(progs, domain, state, parents):
    chain = []
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


