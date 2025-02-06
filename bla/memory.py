from typing import Any, Iterable
from dataclasses import dataclass

Memory = tuple[Any, ...]


class VarType:
    def __init__(self, domain: Iterable[Any], init: Any):
        assert isinstance(domain, Iterable), "Domain must be iterable"
        self._domain = set(domain)

        self.validate(init)
        self._init = init

    def init(self) -> Any:
        return self._init

    def validate(self, val: Any) -> None:
        assert val in self._domain, f"Invalid value {val}"


class BoolType(VarType):
    def __init__(self, domain: Iterable[bool] = [True, False], init: bool = False):
        super().__init__(domain=domain, init=init)


class IntType(VarType):
    def __init__(self, domain: Iterable[int], init: int):
        super().__init__(domain=domain, init=init)
        assert all(isinstance(x, int) for x in self._domain)


@dataclass(frozen=True)
class Reference:
    name: str

    def __repr__(self):
        return self.name


class MemMap:
    def __init__(self, vars: list[tuple[Reference, VarType]]):
        self._types = [t for _, t in vars]
        self._addr = {ref: i for i, (ref, _) in enumerate(vars)}

    def init(self) -> Memory:
        return Memory(t.init() for t in self._types)

    def addr(self, ref: Reference) -> int:
        assert ref in self._addr, f"Unknown variable {ref}"
        return self._addr[ref]

    def validate(self, ref: Reference, val: Any) -> None:
        self._types[self.addr(ref)].validate(val)

    def dump(self, mem: Memory) -> dict[Reference, Any]:
        return {k: mem[addr] for k, addr in self._addr.items()}


def make_var_type(hint: Any) -> VarType:
    match hint:
        case VarType() as vt:
            return vt
        case True | False as b:
            return BoolType(init=b)
        case range() as rng:
            return IntType(domain=rng, init=rng.start)
        case [init, *_] as ints:
            return IntType(domain=ints, init=init)
        case _:
            raise Exception(f"Unsupported type hint {hint}")


def make_mem_map(vars: dict[str, Any]) -> MemMap:
    return MemMap(
        [(Reference(name), make_var_type(hint)) for name, hint in vars.items()]
    )
