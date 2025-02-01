from typing import Callable

from bla.core import Variables, Assertion, State, StateView, FailedAssert
from bla.parse import parse_program
from tabulate import tabulate


def _run_asserts(
    asserts: list[Assertion], sv: StateView, cyclic: bool
) -> FailedAssert | None:
    for a in asserts:
        try:
            a.check(sv, cyclic=cyclic)
        except FailedAssert as e:
            return e
    return None


def proof(
    fns: list[Callable],
    domain: type[Variables],
    assertions: list[Assertion] | None = None,
) -> bool:
    if assertions is None:
        assertions = []
    progs = []
    for fn in fns:
        prog, asserts = parse_program(fn, domain)
        progs.append(prog)
        assertions += asserts

    state = State(pos=tuple([0] * len(progs)), val=tuple([False] * len(domain)))

    stack = [state]
    visited: dict[State, State | None] = {state: None}
    while stack:
        state = stack.pop()
        sv = StateView(state, progs)

        if e := _run_asserts(assertions, sv, cyclic=False):
            explain(sv, domain, visited)
            print(f"Assertion failed: {e}")
            return False

        for ip, prog in enumerate(progs):
            pos = state.pos[ip]
            if pos >= len(prog.ops):
                continue
            npos, nv = prog.run(pos, state.val)
            nxt = State(
                pos=tuple(state.pos[:ip] + (npos,) + state.pos[ip + 1 :]), val=nv
            )

            if nxt in visited:  # Detected cycle
                if e := _run_asserts(assertions, sv, cyclic=True):
                    explain(sv, domain, visited)
                    print(f"Assertion failed: {e}")
                    return False
                continue

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
