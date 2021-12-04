from __future__ import annotations
from typing import (
    BinaryIO,
    ClassVar,
    Iterable,
    Mapping,
    MutableMapping,
    List,
    Optional,
    Union,
)

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


def _unpack_integral_type(
    buffer: bytes, size: int, signed: bool, endianness: Endianness
) -> int:
    if endianness == endianness.BIG:
        buffer = buffer[::-1]
    num = 0
    assert len(buffer) == size
    for i in range(size):
        num |= buffer[i] << (8 * i)
    sign_bit = 0x80 << (8 * (size - 1))
    if signed and (num & sign_bit):
        mask = sum(0xFF << (i * 8) for i in range(size))
        return -((~num + 1) & mask)
    return num


class AddressableStream:
    stream: BinaryIO
    address: int

    def __init__(self, stream: BinaryIO, address: int = 0) -> None:
        self.stream = stream
        self.address = address

    def read_exactly(self, n: int) -> bytes:
        result = b""
        while len(result) < n:
            buffer = self.stream.read(n - len(result))
            if len(buffer) == 0:
                raise IOError("Unexpected end of stream")
            result += buffer
        return result


class Value(ABC):
    CompatibleType = Union[
        "Value", str, int, bytes, float, Iterable["CompatibleType"]
    ]

    # must be specified in instantiated subclasses
    type: ClassVar[basetypes.Type]

    address_base: Optional[Value]
    offset: Optional[int]

    @abstractmethod
    def __init__(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> None:
        self.address_base: Optional[Value] = address_base
        self.offset: Optional[int] = offset

    @classmethod
    def unpack_from_buffer(
        cls,
        buffer: bytes,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        raise NotImplementedError()

    @classmethod
    def cast(
        cls,
        value: CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> Value:
        raise TypeError(
            f"Type {cls.type} cannot be assigned from {type(value)}"
        )

    @abstractmethod
    def initialize_default(self) -> None:
        raise NotImplementedError()

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

    def ref(self) -> PointerValue:
        pointer_type = self.namespace.get_pointer_class_for_type(self.type)
        return pointer_type(referenced_value=self)

    @abstractmethod
    def pack(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def iter_referenced_values(self) -> Iterable[Value]:
        raise NotImplementedError


class IntValue(Value):
    type: basetypes.BaseType

    def __init__(
        self,
        value: Optional[int] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(address_base, offset)
        self.value: Optional[int] = value

    @classmethod
    def unpack_from_buffer(
        cls,
        buffer: bytes,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        assert cls.type.size is not None
        if len(buffer) != cls.type.size:
            raise ValueError(
                f"Invalid length to unpack type {cls.type}: "
                f"need {cls.type.size} bytes, got {len(buffer)}"
            )
        val = _unpack_integral_type(
            buffer,
            cls.type.size,
            cls.type.is_signed,
            cls.type.namespace.arch.endianness,
        )
        return cls(value=val, address_base=address_base, offset=offset)

    @classmethod
    def cast(
        cls,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> IntValue:
        if cls.type.size is None:
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
            mask = sum(0xFF << (i * 8) for i in range(cls.type.size))
            return cls(
                value=int_val & mask,
                address_base=address_base,
                offset=offset,
            )

        raise TypeError(
            f"Type {cls.type} cannot be assigned from {type(value)}"
        )

    def initialize_default(self) -> None:
        if self.is_initialized():
            return
        self.value = 0

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
        return self.__class__(
            value=self.value,
            address_base=address_base,
            offset=offset,
        )

    def __repr__(self) -> str:
        value_str = (
            str(self.value) if self.value is not None else "<uninitialized>"
        )
        return f"<{self.type.name} {value_str}>"

    def __str__(self) -> str:
        return str(self.value) if self.value is not None else "<uninitialized>"

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


class ArrayValue(Value):
    type: basetypes.ArrayType

    def __init__(
        self,
        values: Optional[List[Value]] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(address_base, offset)

        value_class = self.namespace.get_class_for_type(self.type.member_type)
        assert self.type.member_type.size is not None
        if values is None:
            self.values: List[Value] = [
                value_class(
                    address_base=self,
                    offset=i * self.type.member_type.size,
                )
                for i in range(self.type.count)
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

    @classmethod
    def unpack_from_buffer(
        cls,
        buffer: bytes,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        assert cls.type.member_type.size is not None
        count = cls.type.count
        item_size = cls.type.member_type.size
        assert len(buffer) == count * item_size

        member_class = cls.type.namespace.get_class_for_type(
            cls.type.member_type
        )
        vals = []
        item_offset = 0
        for i in range(count):
            vals.append(
                member_class.unpack_from_buffer(
                    buffer[item_offset : item_offset + item_size],
                )
            )
            item_offset += item_size
        return cls(vals, address_base=address_base, offset=offset)

    def initialize_default(self) -> None:
        if self.is_initialized():
            return
        for val in self.values:
            val.initialize_default()

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        yield from self.values

    @classmethod
    def cast(
        cls,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> ArrayValue:
        if not isinstance(value, Iterable):
            raise TypeError(
                f"Type {cls.type} cannot be assigned from {type(value)}"
            )
        value_list = list(value)
        if len(value_list) > cls.type.count:
            raise TypeError(
                f"Too many elements ({len(value_list)}) to fit in {cls.type}"
            )

        values: List[Value] = []
        member_value_class = cls.type.namespace.get_class_for_type(
            cls.type.member_type
        )
        for item in value_list:
            values.append(member_value_class.cast(item))

        padding = cls.type.count - len(value_list)
        for _ in range(padding):
            val = member_value_class()
            val.initialize_default()
            values.append(val)

        return cls(values, address_base, offset)

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> ArrayValue:
        return self.__class__(
            values=self.values,
            address_base=address_base,
            offset=offset,
        )

    def is_initialized(self) -> bool:
        return all(val.is_initialized() for val in self.values)

    def __repr__(self) -> str:
        if self.is_initialized():
            if self.type.member_type.name == "char":
                char_vals = []
                for val in self.values:
                    assert isinstance(val, IntValue) and val.type.size == 1
                    if val.value == 0:
                        break
                    char_vals.append(val.value)
                return f"(char[{self.type.count}]){bytes(char_vals)!r}"
            else:
                return "{" + ", ".join(str(val) for val in self.values) + "}"
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
        super().__init__(address_base, offset)
        self.values: List[Value] = []
        assert self.type.size is not None
        self.values = values
        for i, val in enumerate(self.values):
            val.move(address_base=self, offset=i * self.type.size)

    @classmethod
    def unpack_from_buffer(
        cls,
        buffer: bytes,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        raise NotImplementedError()

    @classmethod
    def cast(
        cls,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> Value:
        raise TypeError(
            f"Type {cls.type} cannot be assigned from {type(value)}"
        )

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        yield from self.values

    def initialize_default(self) -> None:
        if self.is_initialized():
            return
        for val in self.values:
            val.initialize_default()

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> BufferValue:
        return BufferValue(
            [val.copy() for val in self.values],
            address_base=address_base,
            offset=offset,
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
    type: ClassVar[basetypes.PointerType]
    raw_value: Optional[int]

    def __init__(
        self,
        referenced_value: Optional[Value] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
        raw_value: int = None,
    ):
        super().__init__(address_base, offset)
        if referenced_value is not None and raw_value is not None:
            raise ValueError(
                "Cannot have both a referenced object and a raw value."
            )
        self.referenced_value: Optional[Value] = referenced_value
        self.raw_value = raw_value

    @classmethod
    def unpack_from_buffer(
        cls,
        buffer: bytes,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        val = _unpack_integral_type(
            buffer,
            cls.type.namespace.arch.pointer_size,
            False,
            cls.type.namespace.arch.endianness,
        )
        return cls(address_base=address_base, offset=offset, raw_value=val)

    @classmethod
    def cast(
        cls,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> PointerValue:
        if isinstance(value, str):
            value = value.encode("utf-8")

        if isinstance(value, Iterable):
            referenced_value_class = cls.type.namespace.get_class_for_type(
                cls.type.referenced_type
            )
            buffer = BufferValue(
                [referenced_value_class.cast(v).copy() for v in value],
            )
            return cls(
                referenced_value=buffer,
                address_base=address_base,
                offset=offset,
            )
        elif isinstance(value, int):
            return cls(
                address_base=address_base,
                offset=offset,
                raw_value=value,
            )
        raise TypeError(
            f"Type {cls.type} cannot be assigned from {type(value)}"
        )

    def initialize_default(self) -> None:
        if self.is_initialized():
            return
        self.referenced_value = None
        self.raw_value = 0

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        if self.referenced_value is not None:
            yield self.referenced_value

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> PointerValue:
        return self.__class__(
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

    def __str__(self) -> str:
        pointed_type = (
            self.referenced_value.type.name
            if self.referenced_value is not None
            else "void"
        )
        if self.pointed_address is None:
            addr = "NULL"
        else:
            addr = f"0x{self.pointed_address:x}"
        return f"({pointed_type}*){addr}"

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
    type: ClassVar[basetypes.StructType]
    fields: MutableMapping[str, Value]
    field_types: Mapping[str, basetypes.Type]

    def __init__(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
        **kwargs: Value.CompatibleType,
    ):
        self._initialized: bool = False
        super().__init__(address_base, offset)
        self.fields = {
            field.name: self.type.namespace.get_class_for_type(
                field.field_type
            )(address_base=self, offset=field.offset)
            for field in self.type.fields
        }
        self.field_types = {
            field.name: field.field_type for field in self.type.fields
        }
        self._initialized = True
        for field_name, value in kwargs.items():
            setattr(self, field_name, value)

    @classmethod
    def unpack_from_buffer(
        cls,
        buffer: bytes,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        assert len(buffer) == cls.type.size
        values = {}
        for field in cls.type.fields:
            field_class = field.field_type.namespace.get_class_for_type(
                field.field_type
            )
            assert field.size is not None
            buffer_part = buffer[field.offset : field.offset + field.size]
            values[field.name] = field_class.unpack_from_buffer(buffer_part)
        return cls(address_base=address_base, offset=offset, **values)

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        yield from self.fields.values()

    @classmethod
    def cast(
        cls,
        value: Value.CompatibleType,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> StructValue:
        if isinstance(value, StructValue) and value.type == cls.type:
            return value
        raise TypeError(
            f"Type {cls.type} cannot be assigned from {type(value)}"
        )

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> StructValue:
        struct = self.__class__(address_base=address_base, offset=offset)
        for name, field in self.fields.items():
            setattr(struct, name, field)
        return struct

    def initialize_default(self) -> None:
        if self.is_initialized():
            return
        for val in self.fields.values():
            val.initialize_default()

    def is_initialized(self) -> bool:
        return all(val.is_initialized() for val in self.fields.values())

    def __repr__(self):
        fields = " ".join(
            f"{field.name}={self.fields[field.name]}"
            for field in self.type.fields
        )
        addr = f"0x{self.address:x}" if self.address is not None else "None"
        return f"<struct {self.type.name} @{addr}: {fields})>"

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

        value_class = self.type.namespace.get_class_for_type(field_type)
        if isinstance(val, value_class):
            wrappedVal = val.copy(address_base=self, offset=offset)
        else:
            wrappedVal = value_class.cast(
                val, address_base=self, offset=offset
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
