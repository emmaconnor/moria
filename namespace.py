from __future__ import annotations
from typing import (
    Iterable,
    MutableMapping,
    List,
    Set,
)

# we already have a "Type" class, so we need to avoid a name conflict here
from typing import Type as PyType
import re
from arch import Arch

import basetypes
from values import TypedStructValue, Value


class Namespace:
    arch: Arch
    struct_types: MutableMapping[str, PyType[TypedStructValue]]

    def __init__(self, arch: Arch) -> None:
        self.arch = arch
        self.structs: MutableMapping[str, basetypes.StructType] = {}
        self.struct_types = {}

    def pack_values(
        self, base_address: int, max_size: int, values: Iterable[Value]
    ) -> bytes:
        start_address = base_address
        end_address = base_address + max_size
        all_values: Set[Value] = set()
        to_traverse: List[Value] = list(values)
        while len(to_traverse) > 0:
            val = to_traverse.pop()
            all_values.add(val)
            for child in val.iter_referenced_values():
                if child not in all_values:
                    to_traverse.append(child)

        packed_values: List[Value] = []
        for val in all_values:
            if val.address_base is None and val.offset is None:
                assert val.type.size is not None
                assert start_address + val.type.size < end_address
                val.offset = start_address
                start_address += val.type.size
                packed_values.append(val)

        return b"".join(val.pack() for val in packed_values)

    def get_or_create_struct_type(self, name: str) -> basetypes.StructType:
        struct = self.structs.get(name)
        if struct is not None:
            return struct
        struct = basetypes.StructType(self, name)
        self.structs[name] = struct
        return struct

    def format_struct_name(self, name: str) -> str:
        assert (
            re.fullmatch("[a-zA-Z_][a-zA-Z_0-9]*", name) is not None
        ), f"Invalid struct name {name}"
        return name

    def __getattr__(self, name: str) -> PyType[TypedStructValue]:
        if name in self.struct_types:
            return self.struct_types[name]
        raise AttributeError

    def create_types(self) -> None:
        for struct in self.structs.values():
            struct_name = self.format_struct_name(struct.name)
            struct_class = type(
                struct_name, (TypedStructValue,), {"type": struct}
            )
            assert not hasattr(self, struct_name), (
                f"Struct name {struct_name} conflicts "
                "with existing namespace field"
            )

            self.struct_types[struct_name] = struct_class

    def print_structs(self):
        for i, struct in enumerate(self.structs.values()):
            if i > 0:
                print()
            struct.print_struct()
