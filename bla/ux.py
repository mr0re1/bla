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
    render = render or LongStacktrace()

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


class LongStacktrace:
    def __init__(self):
        from tabulate import tabulate  # check dependencies

    def render(self, ctx: ProofCtx):
        from tabulate import tabulate

        if not ctx.failure:
            print("No assertions failed")
            return

        chain = traceback(ctx)

        for i, frame in enumerate(reversed(chain)):
            state = frame.state
            print(f"----- step #{i}:")

            pgs = [ctx.progs[pi].render(pos) for pi, pos in enumerate(state.pos)]
            vls = "\n".join(
                [f"{ref}={val}" for ref, val in ctx.mm.dump(state.val).items()]
            )
            tbl = [pgs + [vls]]
            print(tabulate(tbl, tablefmt="presto"))
            print("\n")

        print(f"Assertion failed: {ctx.failure.error}")


# class OneLiner:
#   def __init__(self):
#     pass

#   def render(self, ctx: ProofCtx):
#     if not ctx.failure:
#       print("OK")
#       return


#     print(f"FAIL: {ctx.failure.error}")
