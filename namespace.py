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

    Char: basetypes.BaseType
    UnsignedChar: basetypes.BaseType
    Short: basetypes.BaseType
    UnsignedShort: basetypes.BaseType
    Int: basetypes.BaseType
    UnsignedInt: basetypes.BaseType
    Long: basetypes.BaseType
    UnsignedLong: basetypes.BaseType
    LongLong: basetypes.BaseType
    UnsignedLongLong: basetypes.BaseType

    Int8: basetypes.BaseType
    UInt8: basetypes.BaseType
    Int16: basetypes.BaseType
    UInt16: basetypes.BaseType
    Int32: basetypes.BaseType
    UInt32: basetypes.BaseType
    Int64: basetypes.BaseType
    UInt64: basetypes.BaseType

    def __init__(self, arch: Arch) -> None:
        self.arch = arch
        self.structs: MutableMapping[str, basetypes.StructType] = {}
        self.struct_types = {}
        self._create_default_types()

    def _create_default_types(self) -> None:
        self.Char = basetypes.BaseType(
            self, "char", self.arch.char_size, _signed=True
        )
        self.UnsignedChar = basetypes.BaseType(
            self, "unsigned char", self.arch.char_size, _signed=False
        )
        self.Short = basetypes.BaseType(
            self, "short", self.arch.short_size, _signed=True
        )
        self.UnsignedShort = basetypes.BaseType(
            self, "unsigned short", self.arch.short_size, _signed=False
        )
        self.Int = basetypes.BaseType(
            self, "int", self.arch.int_size, _signed=True
        )
        self.UnsignedInt = basetypes.BaseType(
            self, "unsigned int", self.arch.int_size, _signed=False
        )
        self.Long = basetypes.BaseType(
            self, "long", self.arch.long_size, _signed=True
        )
        self.UnsignedLong = basetypes.BaseType(
            self, "unsigned long", self.arch.long_size, _signed=False
        )
        self.LongLong = basetypes.BaseType(
            self, "long_long", self.arch.long_long_size, _signed=True
        )
        self.UnsignedLongLong = basetypes.BaseType(
            self, "unsigned long long", self.arch.long_long_size, _signed=False
        )

        self.Int8 = basetypes.BaseType(self, "int8_t", 1, _signed=True)
        self.UInt8 = basetypes.BaseType(self, "uint8_t", 1, _signed=False)
        self.Int16 = basetypes.BaseType(self, "int16_t", 2, _signed=True)
        self.UInt16 = basetypes.BaseType(self, "uint16_t", 2, _signed=False)
        self.Int32 = basetypes.BaseType(self, "int32_t", 4, _signed=True)
        self.UInt32 = basetypes.BaseType(self, "uint32_t", 4, _signed=False)
        self.Int64 = basetypes.BaseType(self, "int64_t", 8, _signed=True)
        self.UInt64 = basetypes.BaseType(self, "uint64_t", 8, _signed=False)

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

    def _format_struct_name(self, name: str) -> str:
        if re.fullmatch("[a-zA-Z_][a-zA-Z_0-9]*", name) is None:
            raise ValueError(f"Invalid struct name {name}")
        return name

    def __getattr__(self, name: str) -> PyType[TypedStructValue]:
        if name in self.struct_types:
            return self.struct_types[name]
        raise AttributeError

    def create_types(self) -> None:
        for struct in self.structs.values():
            struct_name = self._format_struct_name(struct.name)
            struct_class = type(
                struct_name, (TypedStructValue,), {"type": struct}
            )
            if hasattr(self, struct_name):
                raise ValueError(
                    f"Struct name {struct_name} conflicts "
                    "with existing namespace field"
                )

            self.struct_types[struct_name] = struct_class

    def print_structs(self):
        for i, struct in enumerate(self.structs.values()):
            if i > 0:
                print()
            struct.print_struct()
