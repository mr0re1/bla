from typing import Callable

from bla.memory import MemMap, make_mem_map
from bla.core import State, FailedAssert, Prog
from bla.parse import parse_program
from tabulate import tabulate
from dataclasses import dataclass, field


@dataclass(frozen=True)
class _RunFailure:
    state: State
    prog_idx: int
    error: FailedAssert


@dataclass
class _ProofCtx:
    progs: list[Prog]
    mm: MemMap
    parent: dict[State, State | None] = field(default_factory=dict)
    failure: _RunFailure | None = None


def _run(ctx: _ProofCtx, init_state: State) -> bool:
    """
    Runs until either all possible state transitions are exhausted of assert failure occurs.
    Returns True if exhausted, False if assertion failed.
    Affects ctx.
    """
    if init_state in ctx.parent:
        return True

    ctx.parent[init_state] = None
    # NOTES: Assumes that init_state is not in atomic context.
    stack: list[tuple[State, list[int] | None]] = [(init_state, None)]

    while stack:
        state, nxt_progs = stack.pop()

        if nxt_progs is None:
            nxt_progs = list(range(len(ctx.progs)))

        for ip in nxt_progs:
            prog = ctx.progs[ip]

            pos = state.pos[ip]
            if pos >= len(prog.ops):
                continue  # halted

            try:
                npos, nv, atomic = prog.run(pos, state.val)
            except FailedAssert as fa:
                ctx.failure = _RunFailure(state, ip, fa)
                return False

            nxt_state = State(
                pos=tuple(state.pos[:ip] + (npos,) + state.pos[ip + 1 :]), val=nv
            )

            if nxt_state in ctx.parent:  # Detected cycle
                continue

            nxt_progs = None if not atomic else [ip]

            stack.append((nxt_state, nxt_progs))
            ctx.parent[nxt_state] = state
    return True


def proof(
    fns: list[Callable],
    domain: dict[str, type],
) -> bool:
    mm = make_mem_map(domain)
    progs = [parse_program(fn, mm) for fn in fns]
    ctx = _ProofCtx(progs=progs, mm=mm)
    init_state = State(pos=tuple([0] * len(ctx.progs)), val=ctx.mm.init())

    if _run(ctx, init_state):
        return True

    explain(ctx)
    return False


def explain(ctx: _ProofCtx):
    assert ctx.failure

    chain = []
    state: State | None = ctx.failure.state
    while state is not None:
        chain.append(state)
        state = ctx.parent.get(state)

    for i, state in enumerate(reversed(chain)):
        print(f"----- step #{i}:")

        pgs = [ctx.progs[pi].render(pos) for pi, pos in enumerate(state.pos)]
        vls = "\n".join([f"{ref}={val}" for ref, val in ctx.mm.dump(state.val).items()])
        tbl = [pgs + [vls]]
        print(tabulate(tbl, tablefmt="presto"))
        print("\n")

    print(f"Assertion failed: {ctx.failure.error}")
