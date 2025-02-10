from bla.memory import MemMap
from bla.core import State, FailedAssert, Prog
from dataclasses import dataclass, field
from collections import deque


@dataclass(frozen=True)
class RunFailure:
    state: State
    prog_idx: int
    error: FailedAssert


@dataclass
class ProofCtx:
    progs: list[Prog]
    mm: MemMap
    parent: dict[State, State | None] = field(default_factory=dict)
    failure: RunFailure | None = None


def _run(ctx: ProofCtx, init_state: State):
    """
    Runs until either all possible state transitions are exhausted of assert failure occurs.
    Affects ctx.
    """
    if init_state in ctx.parent:
        return

    ctx.parent[init_state] = None
    # NOTES: Assumes that init_state is not in atomic context.
    q: deque[tuple[State, list[int] | None]] = deque([(init_state, None)])

    while q:
        state, nxt_progs = q.popleft()

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
                ctx.failure = RunFailure(state, ip, fa)
                return

            nxt_state = State(
                pos=tuple(state.pos[:ip] + (npos,) + state.pos[ip + 1 :]), val=nv
            )

            if nxt_state in ctx.parent:  # Detected cycle
                continue

            nxt_progs = None if not atomic else [ip]

            q.append((nxt_state, nxt_progs))
            ctx.parent[nxt_state] = state
    return


def run_proof(progs: list[Prog], mm: MemMap) -> ProofCtx:
    ctx = ProofCtx(progs=progs, mm=mm)
    init_state = State(pos=tuple([0] * len(ctx.progs)), val=ctx.mm.init())
    _run(ctx, init_state)
    return ctx
