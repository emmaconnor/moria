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
from values import TypedStructValue, Value, TypedIntValue


class Namespace:
    arch: Arch
    struct_types: MutableMapping[str, PyType[TypedStructValue]]

    Char: PyType[TypedIntValue]
    UnsignedChar: PyType[TypedIntValue]
    Short: PyType[TypedIntValue]
    UnsignedShort: PyType[TypedIntValue]
    Int: PyType[TypedIntValue]
    UnsignedInt: PyType[TypedIntValue]
    Long: PyType[TypedIntValue]
    UnsignedLong: PyType[TypedIntValue]
    LongLong: PyType[TypedIntValue]
    UnsignedLongLong: PyType[TypedIntValue]

    Int8: PyType[TypedIntValue]
    UInt8: PyType[TypedIntValue]
    Int16: PyType[TypedIntValue]
    UInt16: PyType[TypedIntValue]
    Int32: PyType[TypedIntValue]
    UInt32: PyType[TypedIntValue]
    Int64: PyType[TypedIntValue]
    UInt64: PyType[TypedIntValue]

    def __init__(self, arch: Arch) -> None:
        self.arch = arch
        self.structs: MutableMapping[str, basetypes.StructType] = {}
        self.struct_types = {}
        self._create_default_types()

    def _create_typed_integer_class(
        self, name: str, size: int, signed: bool
    ) -> PyType[TypedIntValue]:
        fixed_int_type = basetypes.BaseType(self, name, size, _signed=signed)

        class typed_int_class(TypedIntValue):
            int_type = fixed_int_type

        return typed_int_class

    def _create_default_types(self) -> None:
        self.Char = self._create_typed_integer_class(
            "char", self.arch.char_size, True
        )
        self.UnsignedChar = self._create_typed_integer_class(
            "unsigned char", self.arch.char_size, False
        )
        self.Short = self._create_typed_integer_class(
            "short", self.arch.short_size, True
        )
        self.UnsignedShort = self._create_typed_integer_class(
            "unsigned short", self.arch.short_size, False
        )
        self.Int = self._create_typed_integer_class(
            "int", self.arch.int_size, True
        )
        self.UnsignedInt = self._create_typed_integer_class(
            "unsigned int", self.arch.int_size, False
        )
        self.Long = self._create_typed_integer_class(
            "long", self.arch.long_size, True
        )
        self.UnsignedLong = self._create_typed_integer_class(
            "unsigned long", self.arch.long_size, False
        )
        self.LongLong = self._create_typed_integer_class(
            "long_long", self.arch.long_long_size, True
        )
        self.UnsignedLongLong = self._create_typed_integer_class(
            "unsigned long long", self.arch.long_long_size, False
        )

        self.Int8 = self._create_typed_integer_class("int8_t", 1, True)
        self.UInt8 = self._create_typed_integer_class("uint8_t", 1, False)
        self.Int16 = self._create_typed_integer_class("int16_t", 2, True)
        self.UInt16 = self._create_typed_integer_class("uint16_t", 2, False)
        self.Int32 = self._create_typed_integer_class("int32_t", 4, True)
        self.UInt32 = self._create_typed_integer_class("uint32_t", 4, False)
        self.Int64 = self._create_typed_integer_class("int64_t", 8, True)
        self.UInt64 = self._create_typed_integer_class("uint64_t", 8, False)

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
