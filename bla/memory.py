from typing import Any, Protocol
from dataclasses import dataclass
from inspect import isclass

Memory = tuple[Any, ...]


class VarType(Protocol):
    def init(self) -> Any:
        ...

    def validate(self, val: Any) -> None:
        ...


class BoolType:
    def __init__(self, frm: Any):
        if isclass(frm) and issubclass(frm, bool):
            self._def = False
        elif isinstance(frm, bool):
            self._def = frm
        else:
            raise ValueError(f"Can't build BoolType from {frm}")

    def init(self) -> Any:
        return self._def

    def validate(self, val: Any) -> None:
        assert val in [True, False], f"Invalid bool value {val}"


@dataclass(frozen=True)
class Reference:
    name: str

    def __repr__(self):
        return self.name


class MemMap:
    def __init__(self, vars: dict[str, Any]):
        self._types = [BoolType(t) for t in vars.values()]
        self._addr = {Reference(var): i for i, var in enumerate(vars)}

    def init(self) -> Memory:
        return Memory(t.init() for t in self._types)

    def addr(self, ref: Reference) -> int:
        assert ref in self._addr, f"Unknown variable {ref}"
        return self._addr[ref]

    def validate(self, ref: Reference, val: Any) -> None:
        self._types[self.addr(ref)].validate(val)

    def dump(self, mem: Memory) -> dict[Reference, Any]:
        return {k: mem[addr] for k, addr in self._addr.items()}
