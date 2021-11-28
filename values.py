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

from basetypes import ArrayType, BaseType, PointerType, StructType, Type


class Value(ABC):
    type: Type
    address_base: Optional[Value]
    offset: Optional[int]

    @property
    def address(self) -> Optional[int]:
        addr = self.offset
        if addr is not None and self.address_base is not None:
            if self.address_base.address is not None:
                return self.address_base.address + addr
            return None
        return addr

    @abstractmethod
    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> Value:
        pass

    @abstractmethod
    def __init__(
        self,
        t: Type,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> None:
        self.type = t
        self.address_base: Optional[Value] = address_base
        self.offset: Optional[int] = offset

    @abstractmethod
    def is_initialized(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_pointer(self) -> PointerValue:
        raise NotImplementedError

    @abstractmethod
    def pack(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def iter_referenced_values(self) -> Iterable[Value]:
        raise NotImplementedError

    @staticmethod
    def get_class_for_type(t: Type) -> PyType[Value]:
        if isinstance(t, ArrayType):
            return ArrayValue
        if isinstance(t, PointerType):
            return PointerValue
        if isinstance(t, StructType):
            return StructValue
        if isinstance(t, BaseType):
            return IntValue
        raise ValueError("unknown type")


class VoidValue(Value):
    def __init__(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(BaseType("void", None), address_base, offset)

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> VoidValue:
        return VoidValue(address_base=address_base, offset=offset)

    def get_pointer(self) -> PointerValue:
        return PointerValue(PointerType(self.type), referenced_value=self)

    def pack(self) -> bytes:
        raise NotImplementedError("Cannot serialize void types")

    def is_initialized(self) -> bool:
        return False


class IntValue(Value):
    type: BaseType

    def __init__(
        self,
        int_type: BaseType,
        value: Optional[int] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(int_type, address_base, offset)
        self.value: Optional[int] = value

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

    def get_pointer(self) -> PointerValue:
        return PointerValue(PointerType(self.type), referenced_value=self)

    def __repr__(self) -> str:
        value_str = (
            str(self.value) if self.value is not None else "<uninitialized>"
        )
        return f"<{self.type.name} {value_str}>"

    def pack(self) -> bytes:
        # TODO support big endian
        assert (
            self.type.size is not None
        ), "Cannot serialize type of unresolved size"
        little_endian_bytes: List[int] = []
        val = self.value
        if val is None:
            val = 0
        while val > 0:
            little_endian_bytes.append(val & 0xFF)
            val = val >> 8
        assert (
            len(little_endian_bytes) <= self.type.size
        ), f"Invalid integer for size {self.type.size}: {self.value}"
        padding = self.type.size - len(little_endian_bytes)
        little_endian_bytes += [0] * padding
        return bytes(little_endian_bytes)


class ArrayValue(Value):
    type: ArrayType

    def __init__(
        self,
        array_type: ArrayType,
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
            assert len(values) == self.type.count
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

    def get_pointer(self) -> PointerValue:
        return PointerValue(PointerType(self.type), referenced_value=self)

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
        elem_type: Type,
        values: Optional[List[Value]] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(elem_type, address_base, offset)
        self.values: List[Value] = []
        if values is not None:
            assert self.type.size is not None
            self.values = [
                val.copy(address_base=self, offset=i * self.type.size)
                for i, val in enumerate(values)
            ]

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        yield from self.values

    def get_pointer(self) -> PointerValue:
        return PointerValue(PointerType(self.type), referenced_value=self)

    def copy(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ) -> BufferValue:
        return BufferValue(
            self.type, self.values, address_base=address_base, offset=offset
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
    type: PointerType

    def __init__(
        self,
        pointer_type: PointerType,
        referenced_value: Optional[Value] = None,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(pointer_type, address_base, offset)
        self.referenced_value: Optional[Value] = referenced_value

    @staticmethod
    def raw(address: int) -> PointerValue:
        return VoidValue(address_base=None, offset=address).get_pointer()

    @staticmethod
    def null() -> PointerValue:
        return PointerValue.raw(0x0)

    def iter_referenced_values(self) -> Iterable[Value]:
        if self.address_base is not None:
            yield self.address_base
        if self.referenced_value is not None:
            yield self.referenced_value

    def get_pointer(self) -> PointerValue:
        return PointerValue(PointerType(self.type), referenced_value=self)

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
        )

    @property
    def pointed_address(self) -> Optional[int]:
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
        # TODO support big endian
        assert (
            self.type.size is not None
        ), "Cannot serialize pointer of unresolved size"
        little_endian_bytes: List[int] = []
        if self.referenced_value is None:
            val = 0
        else:
            val = self.pointed_address
        assert val is not None, (
            "Cannot pack a pointer that references an object with unresolved "
            "address!"
        )
        while val > 0:
            little_endian_bytes.append(val & 0xFF)
            val = val >> 8
        assert len(little_endian_bytes) <= self.type.size, (
            f"Invalid address for size {self.type.size}: "
            "0x{self.pointed_address:x}"
        )
        padding = self.type.size - len(little_endian_bytes)
        little_endian_bytes += [0] * padding
        return bytes(little_endian_bytes)


class StructValue(Value):
    type: StructType

    def __init__(
        self,
        struct_type: StructType,
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

    def get_pointer(self) -> PointerValue:
        return PointerValue(PointerType(self.type), referenced_value=self)

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

    def __setattr__(self, name: str, val: Union[Value, int, str]) -> None:
        if name == "_initialized" or not self._initialized:
            return super().__setattr__(name, val)

        if name not in self.fields:
            return super().__setattr__(name, val)
        field_type = self.fields[name].type
        offset = self.fields[name].offset
        if isinstance(val, int) and isinstance(field_type, BaseType):
            wrappedVal = IntValue(
                field_type, value=val, address_base=self, offset=offset
            )
        elif (
            isinstance(val, str)
            and isinstance(field_type, PointerType)
            and field_type.referenced_type.size == 1
        ):
            char_type = BaseType("char", 1)
            string_buffer = BufferValue(
                char_type,
                [IntValue(char_type, c) for c in val.encode("utf-8")],
            )
            wrappedVal = PointerValue(
                PointerType(field_type),
                referenced_value=string_buffer,
                address_base=self,
                offset=offset,
            )
        elif (
            isinstance(val, str)
            and isinstance(field_type, ArrayType)
            and field_type.member_type.size == 1
        ):
            buf = val.encode("utf-8")
            assert len(buf) <= field_type.count
            padded_buf = buf + b"\0" * (field_type.count - len(buf))
            wrappedVal = ArrayValue(
                field_type,
                values=[IntValue(BaseType("char", 1), c) for c in padded_buf],
                address_base=self,
                offset=offset,
            )
        elif isinstance(val, Value.get_class_for_type(field_type)):
            wrappedVal = val.copy(address_base=self, offset=offset)
        else:
            raise TypeError(
                f"Field type {field_type.name} is not "
                "compatible with python type {type(val)}"
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
            except AssertionError:
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
    type: ClassVar[StructType]

    def __init__(
        self,
        address_base: Optional[Value] = None,
        offset: Optional[int] = None,
    ):
        super().__init__(self.type, address_base=address_base, offset=offset)
