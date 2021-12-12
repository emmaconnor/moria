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
from moria.arch import Arch
from moria.pack import HeapPacker

import moria.basetypes as basetypes
from moria.values import ArrayValue, PointerValue, Value, StructValue, IntValue


class Namespace:
    arch: Arch
    struct_types: MutableMapping[str, PyType[StructValue]]

    Char: PyType[IntValue]
    UnsignedChar: PyType[IntValue]
    Short: PyType[IntValue]
    UnsignedShort: PyType[IntValue]
    Int: PyType[IntValue]
    UnsignedInt: PyType[IntValue]
    Long: PyType[IntValue]
    UnsignedLong: PyType[IntValue]
    LongLong: PyType[IntValue]
    UnsignedLongLong: PyType[IntValue]

    Int8: PyType[IntValue]
    UInt8: PyType[IntValue]
    Int16: PyType[IntValue]
    UInt16: PyType[IntValue]
    Int32: PyType[IntValue]
    UInt32: PyType[IntValue]
    Int64: PyType[IntValue]
    UInt64: PyType[IntValue]

    VoidPointer: PyType[PointerValue]

    _type_classes: MutableMapping[str, PyType[Value]]

    def __init__(self, arch: Arch) -> None:
        self.arch = arch
        self.structs: MutableMapping[str, basetypes.StructType] = {}
        self.struct_types = {}
        self._type_classes = {}
        self._create_default_types()

    def _create_typed_integer_class(
        self, name: str, size: int, signed: bool
    ) -> PyType[IntValue]:
        int_class = self.get_class_for_type(
            basetypes.IntType(self, name, size, _signed=signed)
        )
        assert issubclass(int_class, IntValue)
        return int_class

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
            "long long", self.arch.long_long_size, True
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

        void_pointer_class = self.get_class_for_type(
            basetypes.IntType(self, 'void', None, False).get_pointer_type())
        assert(issubclass(void_pointer_class, PointerValue))
        self.VoidPointer = void_pointer_class

    def array(self, t: PyType[Value], count: int) -> PyType[ArrayValue]:
        array_type = basetypes.ArrayType(self, t.type, count)
        array_class = self.get_class_for_type(array_type)
        assert issubclass(array_class, ArrayValue)
        return array_class

    def pack_values(
        self, base_address: int, max_size: int, values: Iterable[Value]
    ) -> bytes:
        all_values: Set[Value] = set()
        to_traverse: List[Value] = list(values)
        while len(to_traverse) > 0:
            val = to_traverse.pop()
            all_values.add(val)
            for child in val.iter_referenced_values():
                if child not in all_values:
                    to_traverse.append(child)

        free_values: Set[Value] = set()
        fixed_values: Set[Value] = set()
        for val in all_values:
            parent = val
            path_to_parent: List[Value] = [val]
            while parent.address_base is not None:
                parent = parent.address_base
                if parent in path_to_parent:
                    path_to_parent.append(parent)
                    path_str = ' -> '.join(repr(v) for v in path_to_parent)
                    raise ValueError(f'Cyclic address dependency: {path_str}')
                path_to_parent.append(parent)
            if parent.offset is None:
                free_values.add(parent)
            else:
                fixed_values.add(parent)

        packer = HeapPacker(base_address, max_size)
        for val in fixed_values:
            assert val.type.size is not None
            assert val.address is not None
            packer.alloc(val.type.size, val.address)

        for val in free_values:
            assert val.type.size is not None
            val.offset = packer.alloc(val.type.size)

        parts: List[bytes] = []
        vals_to_pack: List[Value] = list(free_values) + list(fixed_values)
        vals_to_pack.sort(key=lambda val: val.address or 0)
        for i, val in enumerate(vals_to_pack):
            assert val.address is not None
            assert val.type.size is not None
            part_end = val.address + val.type.size
            if i < len(vals_to_pack) - 1:
                next_start = vals_to_pack[i+1].address
                assert next_start is not None
                pad = next_start - part_end
            else:
                pad = 0
            parts.append(val.pack() + pad*b'\x00')

        return b"".join(parts)

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

    def __getattr__(self, name: str) -> PyType[StructValue]:
        if name in self.struct_types:
            return self.struct_types[name]
        raise AttributeError

    def initialize_struct_classes(self) -> None:
        for struct_type in self.structs.values():
            struct_name = self._format_struct_name(struct_type.name)
            struct_class = self.get_class_for_type(struct_type)
            assert issubclass(struct_class, StructValue)
            if hasattr(self, struct_name):
                raise ValueError(
                    f"Struct name {struct_name} conflicts "
                    "with existing namespace field"
                )
            self.struct_types[struct_name] = struct_class

    def _get_superclass_for_type(self, t: basetypes.Type) -> PyType[Value]:
        if isinstance(t, basetypes.IntType):
            return IntValue
        elif isinstance(t, basetypes.PointerType):
            return PointerValue
        elif isinstance(t, basetypes.ArrayType):
            return ArrayValue
        elif isinstance(t, basetypes.StructType):
            return StructValue
        raise TypeError("No superclass for type {t}!")

    def get_class_for_type(self, t: basetypes.Type) -> PyType[Value]:
        if t.name in self._type_classes:
            return self._type_classes[t.name]
        else:
            superclass = self._get_superclass_for_type(t)

            class type_class(superclass):
                type = t

            self._type_classes[t.name] = type_class
            return type_class

    def print_structs(self):
        for i, struct in enumerate(self.structs.values()):
            if i > 0:
                print()
            print(struct.pretty_string())
