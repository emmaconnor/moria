from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from typing import Type as PyType

from util import SortedList
import namespace as ns
import values


class Type(ABC):
    namespace: ns.Namespace

    def __init__(self, namespace: ns.Namespace):
        self.namespace = namespace

    def get_pointer_type(self) -> PointerType:
        return PointerType(referenced_type=self)

    @property
    def value_class(self) -> PyType[values.Value]:
        return self.namespace.get_class_for_type(self)

    @property
    def pointer_class(self) -> PyType[values.PointerValue]:
        pointer_class = self.namespace.get_class_for_type(
            self.get_pointer_type()
        )
        assert issubclass(pointer_class, values.PointerValue)
        return pointer_class

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError()

    @property
    @abstractmethod
    def size(self) -> Optional[int]:
        raise NotImplementedError()

    @abstractmethod
    def __hash__(self) -> int:
        raise NotImplementedError()

    @abstractmethod
    def __eq__(self, other: Type) -> bool:
        raise NotImplementedError()


@dataclass
class IntType(Type):
    namespace: ns.Namespace
    _name: str
    _size: Optional[int]
    _signed: Optional[bool] = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_signed(self) -> bool:
        if self._signed is not None:
            return self._signed
        return "unsigned" not in self.name.split()

    @property
    def size(self) -> Optional[int]:
        return self._size

    def __hash__(self) -> int:
        return hash((self.__class__, self.namespace, self._size, self._signed))

    def __eq__(self, other: Type) -> bool:
        return (
            isinstance(other, IntType)
            and other.namespace is self.namespace
            and other._size == self._size
            and other._signed == self._signed
        )

    def __repr__(self) -> str:
        un = "un" if not self.is_signed else ""
        return f"<IntType {self.size} bytes, {un}signed>"

    def __str__(self) -> str:
        return self.name


@dataclass
class ArrayType(Type):
    namespace: ns.Namespace
    member_type: Type
    count: int

    @property
    def name(self) -> str:
        count_repr = str(self.count) if self.count > 0 else ""
        return f"{self.member_type.name}[{count_repr}]"

    @property
    def size(self) -> Optional[int]:
        if self.member_type.size is not None:
            return self.member_type.size * self.count
        return None

    def __hash__(self) -> int:
        return hash(
            (self.__class__, self.namespace, self.member_type, self.count)
        )

    def __eq__(self, other: Type) -> bool:
        return (
            isinstance(other, ArrayType)
            and other.namespace is self.namespace
            and other.member_type == self.member_type
            and other.count == self.count
        )

    def __repr__(self) -> str:
        return f"<ArrayType of {self.count} {self.member_type}>"

    def __str__(self) -> str:
        return f"{self.member_type}[{self.count}]"


class PointerType(Type):
    referenced_type: Type

    def __init__(self, referenced_type: Type, size: Optional[int] = None):
        super().__init__(referenced_type.namespace)
        self.referenced_type = referenced_type
        if size is not None and size != self.size:
            raise ValueError(
                "Inconsistent pointer sizes! Current namespace "
                f"architecture uses {self.size} bytes, but got {size} bytes."
            )

    @property
    def name(self) -> str:
        return f"{self.referenced_type.name}*"

    @property
    def size(self) -> Optional[int]:
        return self.namespace.arch.pointer_size

    def __hash__(self) -> int:
        return hash((self.__class__, self.namespace, self.referenced_type))

    def __eq__(self, other: Type) -> bool:
        return (
            isinstance(other, PointerType)
            and other.namespace is self.namespace
            and other.referenced_type == self.referenced_type
        )

    def __repr__(self) -> str:
        return f"<PointerType to {self.referenced_type}>"

    def __str__(self) -> str:
        return f"{self.referenced_type}*"


@dataclass
class StructField:
    namespace: ns.Namespace
    offset: int
    field_type: Type
    name: str

    def __repr__(self) -> str:
        return f"<StructField {self.field_type.name} {self.name}>"

    def __str__(self) -> str:
        return f"{self.field_type.name} {self.name}"

    @staticmethod
    def compare_offsets(x: StructField, y: StructField) -> int:
        return x.offset - y.offset

    @property
    def size(self) -> Optional[int]:
        return self.field_type.size

    def __hash__(self) -> int:
        return hash(
            (
                self.__class__,
                self.namespace,
                self.offset,
                self.field_type,
                self.name,
            )
        )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, StructField):
            return False
        return (
            isinstance(other, StructType)
            and other.namespace is self.namespace
            and self.offset == other.offset
            and self.field_type == other.field_type
            and self.name == other.name
        )


class StructType(Type):
    _name: str
    fields: SortedList[StructField]

    def __init__(self, namespace: ns.Namespace, name: str) -> None:
        super().__init__(namespace)
        self._name = name
        self.fields = SortedList(key=StructField.compare_offsets)

    def add_field(self, field: StructField) -> None:
        self.fields.insert(field)

    def print_struct(self) -> None:
        print(f"{self.name} {{")
        for field in self.fields:
            print(f"  {field}")
        print(f"}} = {self.size} bytes")

    def __repr__(self) -> str:
        fields = ", ".join(str(field) for field in self.fields)
        return f"<StructType {self.name}: {fields}>"

    def __str__(self) -> str:
        fields = ", ".join(str(field) for field in self.fields)
        return f"{self.name} {{{fields}}}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def size(self) -> Optional[int]:
        if len(self.fields) == 0:
            return None
        last_field = self.fields[len(self.fields) - 1]
        if last_field.size is None:
            return None
        return last_field.offset + last_field.size

    def __hash__(self) -> int:
        return hash((self.__class__, self.namespace, self.name))

    def __eq__(self, other: Type) -> bool:
        return (
            isinstance(other, StructType)
            and other.namespace is self.namespace
            and self.name == other.name
        )
