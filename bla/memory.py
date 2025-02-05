from typing import Any
from bla.core import Memory, Reference


class BaseMemMap:
    def __init__(self, vars: dict[str, type]):
        for var, t in vars.items():
            assert issubclass(
                t, bool
            ), f"Type {t} of {var} is not a bool, nothing else is supported yet"
        # self._types = [bool] * len(vars)
        self._addr = {Reference(var): i for i, var in enumerate(vars)}

    def init(self) -> Memory:
        return Memory([False] * len(self._addr))

    def addr(self, ref: Reference) -> int:
        assert ref in self._addr, f"Unknown variable {ref}"
        return self._addr[ref]

    def validate(self, ref: Reference, val: Any) -> None:
        assert ref in self._addr, f"Unknown variable {ref}"
        assert val in [True, False], f"Invalid value {val} for {ref}"

    def dump(self, mem: Memory) -> dict[Reference, Any]:
        return {k: mem[addr] for k, addr in self._addr.items()}
