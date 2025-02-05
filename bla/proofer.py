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
        progs.append(parse_program(fn, domain))

    state = State(pos=tuple([0] * len(progs)), val=tuple([False] * len(domain)))

    # Stack stores pairs (state, programs_to_run_from_this_state_or_all)
    stack: list[tuple[State, list[int] | None]] = [(state, None)]
    visited: dict[State, State | None] = {state: None}
    while stack:
        state, nxt_progs = stack.pop()
        sv = StateView(state, progs)

        if e := _run_asserts(assertions, sv, cyclic=False):
            explain(sv, domain, visited)
            print(f"Assertion failed: {e}")
            return False

        if nxt_progs is None:
            nxt_progs = list(range(len(progs)))

        for ip in nxt_progs:
            prog = progs[ip]

            pos = state.pos[ip]
            if pos >= len(prog.ops):
                continue

            try:
                npos, nv, atomic = prog.run(pos, state.val)
            except FailedAssert as e:  # TODO: refactor proof
                explain(sv, domain, visited)
                print(f"Assertion failed: {e}")
                return False

            nxt = State(
                pos=tuple(state.pos[:ip] + (npos,) + state.pos[ip + 1 :]), val=nv
            )

            if nxt in visited:  # Detected cycle
                if e := _run_asserts(assertions, sv, cyclic=True):
                    explain(sv, domain, visited)
                    print(f"Assertion failed: {e}")
                    return False
                continue

            nxt_progs = None if not atomic else [ip]

            stack.append((nxt, nxt_progs))
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
