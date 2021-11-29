from __future__ import annotations
from typing import (
    ClassVar,
    Iterable,
    MutableMapping,
    List,
    Optional,
    Union,
)

# we already have a "Type" class, so we need to avoid a name conflict here
from typing import Type as PyType
from abc import ABC, abstractmethod
from arch import Endianness

import namespace as ns
import basetypes


def _pack_integral_type(
    num: int, size: int, signed: bool, endianness: Endianness
) -> bytes:
    n_bits = size * 8
    if signed:
        max_value = 1 << (n_bits) - 1
        min_value = -max_value - 1
    else:
        min_value = 0
        max_value = (1 << (n_bits + 1)) - 1

    un = "un" if not signed else ""
    if not min_value <= num <= max_value:
        raise ValueError(
            f"Cannot represent number {num} in "
            f"{un}signed integral type of size {size} bytes"
        )

    mask = sum(0xFF << (i * 8) for i in range(size))
    num &= mask
    little_endian_bytes = [(num >> (i * 8)) & 0xFF for i in range(size)]
    if endianness == Endianness.BIG:
        return bytes(little_endian_bytes[::-1])
    return bytes(little_endian_bytes)


class Value(ABC):
    CompatibleType = Union[
        "Value", str, int, bytes, float, Iterable["CompatibleType"]
    ]

    type: basetypes.Type
    address_base: Optional[Value]
    offset: Optional[int]

    @abstractmethod
    def __init__(
        self,
        t: basetypes.Type,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> None:
        self.type = t
        self.address_base: Optional[Value] = address_base
        self.offset: Optional[int] = offset

    @staticmethod
    def cast(
        t: basetypes.Type,
        value: CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> Value:
        raise TypeError(f"Type {t} cannot be assigned from {type(value)}")

    def move(
        self,
        address_base: Optional[Value],
        offset: Optional[int],
    ) -> None:
        self.address_base = address_base
        self.offset = offset

    @property
    def address(self) -> Optional[int]:
        """Compute the address of the first byte of the value.
        This may be None if the value has not yet been resolved to an address.
        For values with a base_address value, the address is computed relative
        to this value. Otherwise, offset is used as an absolute address."""
        addr = self.offset
        if addr is not None and self.address_base is not None:
            if self.address_base.address is not None:
                return self.address_base.address + addr
            return None
        return addr

    @property
    def namespace(self) -> ns.Namespace:
        return self.type.namespace

    @abstractmethod
    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> Value:
        raise NotImplementedError

    @abstractmethod
    def is_initialized(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def ref(self) -> PointerValue:
        raise NotImplementedError

    @abstractmethod
    def pack(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def iter_referenced_values(self) -> Iterable[Value]:
        raise NotImplementedError

    @staticmethod
    def get_class_for_type(t: basetypes.Type) -> PyType[Value]:
        if isinstance(t, basetypes.ArrayType):
            return ArrayValue
        if isinstance(t, basetypes.PointerType):
            return PointerValue
        if isinstance(t, basetypes.StructType):
            return StructValue
        if isinstance(t, basetypes.BaseType):
            return IntValue
        raise ValueError("unknown type")


class IntValue(Value):
    type: basetypes.BaseType

    def __init__(
        self,
        int_type: basetypes.BaseType,
        value: Optional[int] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(int_type, address_base, offset)
        self.value: Optional[int] = value

    @staticmethod
    def cast(
        t: basetypes.BaseType,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> IntValue:
        if t.size is None:
            raise ValueError("Cannot cast to integer type without a size")

        int_val: Optional[int] = None
        if isinstance(value, int):
            int_val = value
        elif isinstance(value, float):
            int_val = int(value)
        elif isinstance(value, str) and len(value) == 1:
            int_val = ord(value)
        elif isinstance(value, bytes) and len(value) == 1:
            int_val = value[0]

        if int_val is not None:
            mask = sum(0xFF << (i * 8) for i in range(t.size))
            return IntValue(
                t,
                value=int_val & mask,
                address_base=address_base,
                offset=offset,
            )

        raise TypeError(f"Type {t} cannot be assigned from {type(value)}")

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base

    def is_initialized(self) -> bool:
        return self.value is not None

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> IntValue:
        return IntValue(
            self.type,
            value=self.value,
            address_base=address_base,
            offset=offset,
        )

    def ref(self) -> PointerValue:
        return PointerValue(
            basetypes.PointerType(self.type), referenced_value=self
        )

    def __repr__(self) -> str:
        value_str = (
            str(self.value) if self.value is not None else "<uninitialized>"
        )
        return f"<{self.type.name} {value_str}>"

    def pack(self) -> bytes:
        assert (
            self.type.size is not None
        ), "Cannot serialize type of unresolved size"
        val = self.value
        if val is None:
            val = 0
        return _pack_integral_type(
            val,
            self.type.size,
            signed=self.type.is_signed,
            endianness=self.namespace.arch.endianness,
        )


class TypedIntValue(IntValue):
    int_type: basetypes.BaseType

    def __init__(
        self,
        value: Optional[int] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(self.int_type, value, address_base, offset)


class ArrayValue(Value):
    type: basetypes.ArrayType

    def __init__(
        self,
        array_type: basetypes.ArrayType,
        values: Optional[List[Value]] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(array_type, address_base, offset)

        value_class = Value.get_class_for_type(array_type.member_type)
        assert self.type.member_type.size is not None
        if values is None:
            self.values: List[Value] = [
                value_class(
                    array_type.member_type,
                    address_base=self,
                    offset=i * self.type.member_type.size,
                )
                for i in range(array_type.count)
            ]
        else:
            if len(values) != self.type.count:
                raise ValueError(
                    "Wrong number of values to initialize array. "
                    f"Expected {self.type.count} items, got {len(values)}."
                )
            self.values = [
                val.copy(
                    address_base=self, offset=i * self.type.member_type.size
                )
                for i, val in enumerate(values)
            ]

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        yield from self.values

    @staticmethod
    def cast(
        t: basetypes.ArrayType,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> ArrayValue:
        if not isinstance(value, Iterable):
            raise TypeError(f"Type {t} cannot be assigned from {type(value)}")
        value_list = list(value)
        if len(value_list) > t.count:
            raise TypeError(
                f"Too many elements ({len(value_list)}) to fit in {t}"
            )

        values: List[Value] = []
        member_value_class = Value.get_class_for_type(t.member_type)
        for item in value_list:
            values.append(member_value_class.cast(t.member_type, item))

        padding = t.count - len(value_list)
        for _ in range(padding):
            values.append(member_value_class(t.member_type))

        return ArrayValue(t, values, address_base, offset)

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> ArrayValue:
        return ArrayValue(
            self.type,
            values=self.values,
            address_base=address_base,
            offset=offset,
        )

    def ref(self) -> PointerValue:
        return PointerValue(
            basetypes.PointerType(self.type), referenced_value=self
        )

    def is_initialized(self) -> bool:
        return all(val.is_initialized() for val in self.values)

    def __repr__(self) -> str:
        if self.is_initialized():
            return "{" + ", ".join(repr(val) for val in self.values) + "}"
        else:
            return f"{{<uninitialized>, ... * {self.type.count}}}"

    def pack(self) -> bytes:
        parts: List[bytes] = []

        assert (
            self.type.member_type.size is not None
        ), "Cannot serialize array elements of unresolved size"

        for elem in self.values:
            part = elem.pack()
            assert len(part) == self.type.member_type.size
            parts.append(part)

        return b"".join(parts)


class BufferValue(Value):
    def __init__(
        self,
        values: List[Value],
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        if len(values) == 0:
            raise ValueError("Cannot instantiate empty buffer")
        super().__init__(values[0].type, address_base, offset)
        self.values: List[Value] = []
        assert self.type.size is not None
        self.values = values
        for i, val in enumerate(self.values):
            val.move(address_base=self, offset=i * self.type.size)

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        yield from self.values

    @staticmethod
    def cast(
        t: basetypes.Type,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> BufferValue:
        raise NotImplementedError

    def ref(self) -> PointerValue:
        return PointerValue(
            basetypes.PointerType(self.type), referenced_value=self
        )

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> BufferValue:
        return BufferValue(
            self.values, address_base=address_base, offset=offset
        )

    def is_initialized(self) -> bool:
        return all(val.is_initialized() for val in self.values)

    def pack(self) -> bytes:
        parts: List[bytes] = []

        assert (
            self.type.size is not None
        ), "Cannot serialize array elements of unresolved size"

        for elem in self.values:
            part = elem.pack()
            assert len(part) == self.type.size
            parts.append(part)

        return b"".join(parts)


class PointerValue(Value):
    type: basetypes.PointerType
    raw_value: Optional[int]

    def __init__(
        self,
        pointer_type: basetypes.PointerType,
        referenced_value: Optional[Value] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
        raw_value: int = None,
    ):
        super().__init__(pointer_type, address_base, offset)
        if referenced_value is not None and raw_value is not None:
            raise ValueError("Cannot have both a referenced object and a raw value.")
        self.referenced_value: Optional[Value] = referenced_value
        self.raw_value = raw_value

    @staticmethod
    def cast(
        t: basetypes.PointerType,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> PointerValue:
        if isinstance(value, str):
            value = value.encode("utf-8")

        if isinstance(value, Iterable):
            referenced_value_class = Value.get_class_for_type(t.referenced_type)
            buffer = BufferValue(
                t.referenced_type,
                [
                    referenced_value_class.cast(t.referenced_type, v)
                    for v in value
                ],
            )
            return PointerValue(
                basetypes.PointerType(t),
                referenced_value=buffer,
                address_base=address_base,
                offset=offset,
            )
        elif isinstance(value, int):
            return PointerValue(
                basetypes.PointerType(t),
                address_base=address_base,
                offset=offset,
                raw_value=value,
            )
        raise TypeError(f"Type {t} cannot be assigned from {type(value)}")

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        if self.referenced_value is not None:
            yield self.referenced_value

    def ref(self) -> PointerValue:
        return PointerValue(
            basetypes.PointerType(self.type), referenced_value=self
        )

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> PointerValue:
        return PointerValue(
            self.type,
            referenced_value=self.referenced_value,
            address_base=address_base,
            offset=offset,
            raw_value=self.raw_value,
        )

    @property
    def pointed_address(self) -> Optional[int]:
        if self.raw_value is not None:
            return self.raw_value
        if self.referenced_value is None:
            return None
        if self.referenced_value.address is None:
            return None
        return self.referenced_value.address

    def is_initialized(self) -> bool:
        return self.pointed_address is not None

    def __repr__(self) -> str:
        pointed_type = (
            self.referenced_value.type
            if self.referenced_value is not None
            else "None"
        )
        return f"<PointerValue to {pointed_type}>"

    def pack(self) -> bytes:
        assert (
            self.type.size is not None
        ), "Cannot serialize pointer of unresolved size"

        pointed_address = self.pointed_address
        if pointed_address is None:
            pointed_address = 0

        return _pack_integral_type(
            pointed_address,
            self.type.size,
            signed=False,
            endianness=self.namespace.arch.endianness,
        )


class StructValue(Value):
    type: basetypes.StructType

    def __init__(
        self,
        struct_type: basetypes.StructType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        self._initialized: bool = False
        super().__init__(struct_type, address_base, offset)
        self.fields: MutableMapping[str, Value] = {
            field.name: Value.get_class_for_type(field.field_type)(
                field.field_type, address_base=self, offset=field.offset
            )
            for field in struct_type.fields
        }
        self._initialized = True

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        yield from self.fields.values()

    @staticmethod
    def cast(
        t: basetypes.StructType,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> StructValue:
        if isinstance(value, TypedStructValue) and value.type == t:
            return value
        raise TypeError(f"Type {t} cannot be assigned from {type(value)}")

    def ref(self) -> PointerValue:
        return PointerValue(
            basetypes.PointerType(self.type), referenced_value=self
        )

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> StructValue:
        struct = StructValue(
            self.type, address_base=address_base, offset=offset
        )
        for name, field in self.fields.items():
            setattr(struct, name, field)
        return struct

    def is_initialized(self) -> bool:
        return all(val.is_initialized() for val in self.fields.values())

    def __repr__(self):
        fields = " ".join(
            f"{field.name}={self.fields[field.name]}"
            for field in self.type.fields
        )
        return f"<struct {self.type.name}: {fields})>"

    def __getattr__(self, name: str) -> Value:
        if name == "_initialized" or not self._initialized:
            raise AttributeError(
                f"Struct {self.type.name} has no attribute {name}"
            )
        attr = self.fields[name]
        if attr is not None:
            return attr
        raise AttributeError(f"Struct {self.type.name} has no field {name}")

    def __setattr__(self, name: str, val: Value.CompatibleType) -> None:
        if name == "_initialized" or not self._initialized:
            return super().__setattr__(name, val)

        if name not in self.fields:
            return super().__setattr__(name, val)
        field_type = self.fields[name].type
        offset = self.fields[name].offset

        value_class = Value.get_class_for_type(field_type)
        if isinstance(val, value_class):
            wrappedVal = val.copy(address_base=self, offset=offset)
        else:
            wrappedVal = value_class.cast(
                field_type, val, address_base=self, offset=offset
            )
        self.fields[name] = wrappedVal

    def pack(self) -> bytes:
        parts: List[bytes] = []
        last_field_end = 0
        for type_field in self.type.fields:
            padding = type_field.offset - last_field_end
            assert padding >= 0

            field_value = self.fields[type_field.name]
            try:
                field_bytes = field_value.pack()
            except Exception:
                print(f"unable to pack field {type_field.name}")
                raise

            assert (
                type_field.size is not None
            ), "Cannot serialize field of unresolved size"
            assert len(field_bytes) == type_field.size

            parts.append(b"\x00" * padding + field_bytes)
            last_field_end = type_field.offset + type_field.size

        return b"".join(parts)


class TypedStructValue(StructValue):
    type: ClassVar[basetypes.StructType]

    def __init__(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
        **kwargs: Value.CompatibleType,
    ):
        super().__init__(self.type, address_base=address_base, offset=offset)
        for field_name, value in kwargs.items():
            if field_name in self.fields:
                setattr(self, field_name, value)
            else:
                raise TypeError(f"Unexpected keyword argument: {field_name}")
