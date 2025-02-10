from typing import Callable, Protocol

from dataclasses import dataclass

from bla.memory import make_mem_map
from bla.core import State
from bla.parse import parse_program
from bla.proofer import ProofCtx, run_proof


class ProofRenderer(Protocol):
    def render(self, ctx: ProofCtx) -> None:
        ...


def proof(
    fns: list[Callable], domain: dict[str, type], render: ProofRenderer | None = None
) -> bool:
    render = render or ShortStacktrace()

    mm = make_mem_map(domain)
    progs = [parse_program(fn, mm) for fn in fns]

    ctx = run_proof(progs, mm)
    render.render(ctx)
    return ctx.failure is None


@dataclass(frozen=True)
class TBFrame:
    state: State
    prog_idx: int


def traceback(ctx: ProofCtx) -> list[TBFrame]:
    if not ctx.failure:
        return []

    chain = [TBFrame(ctx.failure.state, ctx.failure.prog_idx)]

    while True:
        nxt = chain[-1].state
        cur: State | None = ctx.parent.get(nxt)
        if cur is None:
            break

        prog_idx = -1
        # find different ellemt
        for p, (n, c) in enumerate(zip(nxt.pos, cur.pos)):
            if n != c:
                prog_idx = p
                break

        chain.append(TBFrame(cur, prog_idx))
    return chain


class ShortStacktrace:
    def __init__(self):
        from tabulate import tabulate  # check dependencies

    def render(self, ctx: ProofCtx):
        if not ctx.failure:
            print("OK")
            return
        from tabulate import tabulate

        tbl = []
        chain = traceback(ctx)[::-1]
        for i, frame in enumerate(chain):
            state = frame.state
            prog_idx = frame.prog_idx
            if prog_idx != -1:
                prog = ctx.progs[prog_idx]
                pos = state.pos[prog_idx]
                prog_name, prog_line = prog.name, prog.render_op(pos)
            else:
                prog_name, prog_line = "???", "???"

            vls = ";".join(
                [f"{ref}={val}" for ref, val in ctx.mm.dump(state.val).items()]
            )

            next = chain[i + 1].state if i + 1 < len(chain) else None
            if not next or next.val != state.val:
                # Only render on changes in memory
                tbl.append([i, prog_name, prog_line, vls])

            prev = state

        print(tabulate(tbl, tablefmt="presto"))
        print(f"FAIL: {ctx.failure.error}")
