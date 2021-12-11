import pytest

from moria.arch import Endianness
from moria.basetypes import IntType, StructField
from moria.values import (
    ArrayValue,
    IntValue,
    PointerValue,
    StructValue,
    Value,
    _pack_integral_type,
)
from tests.helpers import make_namespace, make_namespaces, amd64_namespace


class TestStructValue:
    def test_pack(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        struct_type = ns.get_or_create_struct_type('test')
        struct_type.add_field(StructField(ns, 0, ns.Int.type, 'int_field'))
        struct_type.add_field(StructField(
            ns, 4, struct_type.get_pointer_type(), 'self_ptr'))

        struct_class = ns.get_class_for_type(struct_type)
        assert issubclass(struct_class, StructValue)

        struct = struct_class(int_field=1, self_ptr=2)
        assert struct.pack() == b'\x01\x00\x00\x00' b'\x02\x00\x00\x00'

        unpackable_struct_type = ns.get_or_create_struct_type('unpackable')
        unpackable_struct_type.add_field(StructField(ns, 0, IntType(
            ns, 'partial int', None, False), 'unpackable_field'))
        unpackable_struct_class = ns.get_class_for_type(unpackable_struct_type)
        assert issubclass(unpackable_struct_class, StructValue)
        with pytest.raises(Exception, match='.*unpackable_field.*'):
            unpackable_struct_class().pack()

    def test_repr(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        struct_type = ns.get_or_create_struct_type('test')
        struct_type.add_field(StructField(ns, 0, ns.Int.type, 'int_field'))
        struct_type.add_field(StructField(
            ns, 4, struct_type.get_pointer_type(), 'self_ptr'))

        struct_class = ns.get_class_for_type(struct_type)
        assert issubclass(struct_class, StructValue)

        struct = struct_class(int_field=1, self_ptr=2)

        assert repr(struct) == '<struct test @None: int_field=1 self_ptr=(void*)0x2>'

        struct.move(address_base=None, offset=0)
        assert repr(struct) == '<struct test @0x0: int_field=1 self_ptr=(void*)0x2>'

    def test_cast(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        struct_type = ns.get_or_create_struct_type('test')
        struct_type.add_field(StructField(ns, 0, ns.Int.type, 'int_field'))
        struct_type.add_field(StructField(
            ns, 4, struct_type.get_pointer_type(), 'self_ptr'))

        struct_class = ns.get_class_for_type(struct_type)
        assert issubclass(struct_class, StructValue)

        struct = struct_class.cast(struct_class(int_field=1, self_ptr=2))
        assert isinstance(struct.int_field, IntValue)
        assert int(struct.int_field) == 1
        assert isinstance(struct.self_ptr, PointerValue)
        assert int(struct.self_ptr) == 2

        with pytest.raises(TypeError):
            struct_class.cast('')

    def test_iter_referenced_values(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        struct_type = ns.get_or_create_struct_type('test')
        struct_type.add_field(StructField(ns, 0, ns.Int.type, 'int_field'))
        struct_type.add_field(StructField(
            ns, 4, struct_type.get_pointer_type(), 'self_ptr'))

        struct_class = ns.get_class_for_type(struct_type)
        assert issubclass(struct_class, StructValue)

        arr_class = ns.array(struct_class, 1)
        arr = arr_class([struct_class(int_field=7)])
        struct = arr.values[0]
        assert isinstance(struct, StructValue)

        refs = list(struct.iter_referenced_values())
        assert len(refs) == 3
        assert arr in refs
        assert struct.int_field in refs
        assert struct.self_ptr in refs

    def test_unpack(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        struct_type = ns.get_or_create_struct_type('test')
        struct_type.add_field(StructField(ns, 0, ns.Int.type, 'int_field'))
        struct_type.add_field(StructField(
            ns, 4, struct_type.get_pointer_type(), 'self_ptr'))

        struct_class = ns.get_class_for_type(struct_type)
        assert issubclass(struct_class, StructValue)

        struct = struct_class.unpack_from_buffer(
            b'\x01\x00\x00\x00' b'\x02\x00\x00\x00')
        assert isinstance(struct.int_field, IntValue)
        assert int(struct.int_field) == 1
        assert isinstance(struct.self_ptr, PointerValue)
        assert int(struct.self_ptr) == 2

    def test_struct(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        struct_type = ns.get_or_create_struct_type('test')
        struct_type.add_field(StructField(ns, 0, ns.Int.type, 'int_field'))
        struct_type.add_field(StructField(
            ns, 4, struct_type.get_pointer_type(), 'self_ptr'))

        struct_class = ns.get_class_for_type(struct_type)
        assert issubclass(struct_class, StructValue)

        struct = struct_class(int_field=7)
        assert struct.type.name == 'test'
        assert isinstance(struct.int_field, IntValue)
        assert int(struct.int_field) == 7
        assert isinstance(struct.self_ptr, PointerValue)
        assert struct.self_ptr.pointed_address is None

        with pytest.raises(AttributeError):
            struct.not_a_real_field


class TestPointerValue:
    def test_pack(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        assert ns.VoidPointer.cast(0x04030201).pack() == (b'\x01\x02\x03\x04')
        assert ns.VoidPointer().pack() == (b'\x00\x00\x00\x00')

        ns = make_namespace(endian=Endianness.BIG, word_size=4)
        assert ns.VoidPointer.cast(0x04030201).pack() == (b'\x04\x03\x02\x01')

        ns = make_namespace(endian=Endianness.LITTLE, word_size=8)
        assert ns.VoidPointer.cast(0x0807060504030201).pack() == (
            b'\x01\x02\x03\x04\x05\x06\x07\x08')

        ns = make_namespace(endian=Endianness.BIG, word_size=8)
        assert ns.VoidPointer.cast(0x0807060504030201).pack() == (
            b'\x08\x07\x06\x05\x04\x03\x02\x01')

    def test_conversions(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        ptr = ns.VoidPointer(raw_value=0)
        assert int(ptr) == 0
        assert str(ptr) == "(void*)NULL"

        ptr = ns.VoidPointer(raw_value=1)
        assert int(ptr) == 1
        assert str(ptr) == "(void*)0x1"

        ptr = ns.VoidPointer(raw_value=1)
        assert int(ptr) == 1

        ptr = ns.VoidPointer()
        assert str(ptr) == "(void*)None"
        with pytest.raises(ValueError):
            int(ptr)

        ptr = ptr.ref()
        assert str(ptr) == "(void**)None"
        with pytest.raises(ValueError):
            int(ptr)

    def test_repr(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        ptr = ns.VoidPointer()
        assert repr(ptr) == "<PointerValue to void@None>"

        ptr = ns.VoidPointer(raw_value=0)
        assert repr(ptr) == "<PointerValue to void@0>"

    def test_get_address(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        ptr = ns.VoidPointer()
        assert ptr.pointed_address is None

        ptr_ptr = ptr.ref()
        assert ptr_ptr.pointed_address is None

    def test_copy(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        ptr = ns.VoidPointer.cast(0)
        copy = ptr.copy()
        assert ptr.pointed_address == 0
        assert copy.pointed_address == 0

        ptr.raw_value = 1
        assert ptr.pointed_address == 1
        assert copy.pointed_address == 0

        copy.raw_value = 2
        assert ptr.pointed_address == 1
        assert copy.pointed_address == 2

    def test_iter_referenced_values(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        ptr = ns.VoidPointer.cast(0)
        refs = list(ptr.iter_referenced_values())
        assert len(refs) == 0

        offset_ptr = ns.VoidPointer.cast(0, address_base=ptr, offset=4)
        refs = list(offset_ptr.iter_referenced_values())
        assert len(refs) == 1
        assert refs[0] is ptr

        ptr_ptr = ptr.ref()
        refs = list(ptr_ptr.iter_referenced_values())
        assert len(refs) == 1
        assert refs[0] is ptr

        offset_ptr_ptr = ptr.ref()
        offset_ptr_ptr.move(ptr, 4)
        refs = list(offset_ptr_ptr.iter_referenced_values())
        assert len(refs) == 2
        assert refs == [ptr, ptr]

    def test_cast(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        assert ns.VoidPointer.cast(0).pointed_address == 0

        char_pointer_class = ns.Char.get_pointer_class()
        test_pointer = char_pointer_class.cast('test')
        assert test_pointer.referenced_value is not None
        assert isinstance(test_pointer.referenced_value, ArrayValue)
        assert isinstance(test_pointer.referenced_value.type.member_type, IntType)
        assert test_pointer.referenced_value.type.member_type.size == 1
        assert str(test_pointer.referenced_value) == 'test'

        with pytest.raises(TypeError):
            ns.VoidPointer.cast(1.1)

    def test_unpack(self) -> None:
        ns = make_namespace(endian=Endianness.LITTLE, word_size=4)
        ptr = ns.VoidPointer.unpack_from_buffer(b'\x01\x02\x03\x04')
        assert ptr.pointed_address == 0x04030201

        ns = make_namespace(endian=Endianness.BIG, word_size=4)
        ptr = ns.VoidPointer.unpack_from_buffer(b'\x01\x02\x03\x04')
        assert ptr.pointed_address == 0x01020304

        ns = make_namespace(endian=Endianness.LITTLE, word_size=8)
        ptr = ns.VoidPointer.unpack_from_buffer(b'\x01\x02\x03\x04\x05\x06\x07\x08')
        assert ptr.pointed_address == 0x0807060504030201

        ns = make_namespace(endian=Endianness.BIG, word_size=8)
        ptr = ns.VoidPointer.unpack_from_buffer(b'\x01\x02\x03\x04\x05\x06\x07\x08')
        assert ptr.pointed_address == 0x0102030405060708

    def test_pointer(self) -> None:
        for ns in make_namespaces():
            null_pointer = ns.VoidPointer(raw_value=0)
            assert null_pointer.type.size == ns.arch.pointer_size
            assert null_pointer.pointed_address == 0
            assert null_pointer.address == None
            with pytest.raises(ValueError):
                ns.VoidPointer(referenced_value=null_pointer, raw_value=0)


class TestArrayValue:
    def test_pack(self) -> None:
        ns = amd64_namespace()
        char_arr_class = ns.array(ns.Char, 3)
        char_arr = char_arr_class.cast("hi")
        assert char_arr.pack() == b'hi\x00'

        arr_class = ns.array(ns.Int, 3)
        int_arr = arr_class.cast([0, 1, 2])
        assert int_arr.pack() == (
            b'\x00\x00\x00\x00'
            b'\x01\x00\x00\x00'
            b'\x02\x00\x00\x00'
        )

    def test_conversions(self) -> None:
        ns = amd64_namespace()
        char_arr_class = ns.array(ns.Char, 3)
        char_arr = char_arr_class.cast("hi")

        assert bytes(char_arr) == b'hi'
        assert str(char_arr) == 'hi'
        assert repr(char_arr).replace('"', "'") in "(char[3])b'hi'"

        arr_class = ns.array(ns.Int, 3)
        int_arr = arr_class.cast([0, 1, 2])
        assert repr(int_arr) == '{0, 1, 2}'

        with pytest.raises(TypeError):
            bytes(int_arr)

    def test_cast(self) -> None:
        ns = amd64_namespace()
        arr_class = ns.array(ns.Int, 3)
        arr = arr_class.cast([0, 1, 2])
        assert len(arr) == 3
        assert [int(v) for v in arr.values] == [0, 1, 2]  # type: ignore

        arr = arr_class.cast([1])
        assert len(arr) == 3
        assert int(arr.values[0]) == 1  # type: ignore
        with pytest.raises(ValueError):
            int(arr.values[1])  # type: ignore

        with pytest.raises(TypeError):
            arr_class.cast(0)
        with pytest.raises(TypeError):
            arr_class.cast([0, 1, 2, 3])

    def test_iter_referenced_values(self) -> None:
        ns = amd64_namespace()
        arr_class = ns.array(ns.Int, 3)
        buf = b''.join(ns.Int(i).pack() for i in range(3))
        arr = arr_class.unpack_from_buffer(buf)
        refs = list(arr.iter_referenced_values())
        assert len(refs) == 3
        assert all(isinstance(ref, IntValue) for ref in refs)
        assert sorted(int(ref) for ref in refs) == [0, 1, 2]  # type: ignore

        arr2_class = ns.array(arr_class, 1)
        arr2 = arr2_class.unpack_from_buffer(buf)
        arr = arr2.values[0]

        refs = list(arr.iter_referenced_values())
        assert len(refs) == 4
        int_refs = []
        for ref in refs:
            if isinstance(ref, IntValue):
                int_refs.append(int(ref))
            else:
                assert ref is arr2
        assert sorted(int_refs) == [0, 1, 2]

    def test_array_unpack(self) -> None:
        ns = amd64_namespace()
        arr_class = ns.array(ns.Int, 3)
        buf = b''.join(ns.Int(i).pack() for i in range(3))
        arr = arr_class.unpack_from_buffer(buf)
        assert len(arr) == 3

    def test_array(self) -> None:
        ns = amd64_namespace()
        arr_class = ns.array(ns.Int, 3)
        assert arr_class.type.count == 3

        arr = arr_class()
        assert len(arr.values) == 3

        arr = arr_class.cast([1, 2, 3])
        assert len(arr.values) == 3

        with pytest.raises(ValueError):
            arr_class(values=[])


class TestValue:
    def test_ref(self) -> None:
        num1 = make_namespace(endian=Endianness.LITTLE, word_size=8).Int(
            0, offset=4
        )
        ptr = num1.ref()
        assert isinstance(ptr, PointerValue)
        assert ptr.referenced_value is num1
        assert ptr.pointed_address == 4

    def test_address_and_move(self) -> None:
        num1 = make_namespace(endian=Endianness.LITTLE, word_size=8).Int(
            0, offset=0
        )
        num2 = make_namespace(endian=Endianness.LITTLE, word_size=8).Int(
            1, offset=4
        )
        num3 = make_namespace(endian=Endianness.LITTLE, word_size=8).Int(
            2, address_base=num2, offset=4
        )
        assert num1.address == 0
        assert num2.address == 4
        assert num3.address == 8

        num2.move(None, 8)
        assert num1.address == 0
        assert num2.address == 8
        assert num3.address == 12

        num2.move(None, None)
        assert num1.address == 0
        assert num2.address is None
        assert num3.address is None

    def test_abstract_methods(self) -> None:
        # Instantiate a subclass of Value to invoke abstract Value methods on
        val_obj = make_namespace(endian=Endianness.LITTLE, word_size=8).Int(0)
        with pytest.raises(NotImplementedError):
            Value.unpack_from_buffer(b"")
        with pytest.raises(NotImplementedError):
            Value.cast(0)
        with pytest.raises(NotImplementedError):
            Value.copy(val_obj)
        with pytest.raises(NotImplementedError):
            Value.pack(val_obj)
        with pytest.raises(NotImplementedError):
            Value.iter_referenced_values(val_obj)


class TestInt:
    def test_str_repr(self) -> None:
        for ns in make_namespaces():
            assert str(ns.Int()) == "<uninitialized>"
            assert str(ns.Int(1)) == "1"
            assert str(ns.Int(-1)) == "-1"

            assert repr(ns.Int()) == "<int <uninitialized>>"
            assert repr(ns.Int(1)) == "<int 1>"
            assert repr(ns.Int(-1)) == "<int -1>"

    def test_conversions(self) -> None:
        for ns in make_namespaces():
            a = ns.Int(3)
            assert float(a) == 3.0
            assert int(a) == 3

            with pytest.raises(ValueError):
                float(ns.Int())
            with pytest.raises(ValueError):
                int(ns.Int())

    def test_copy(self) -> None:
        for ns in make_namespaces():
            a = ns.Int(0)
            assert a.value == 0

            b = a.copy()
            assert isinstance(b, IntValue)
            assert a is not b
            assert b.value == 0

            a.value = 1
            assert a.value == 1
            assert b.value == 0

            b.value = 2
            assert a.value == 1
            assert b.value == 2

    def test_iter_referenced_values(self) -> None:
        for ns in make_namespaces():
            a = ns.Int(0)
            b = ns.Int(0, address_base=a, offset=4)
            assert len(list(a.iter_referenced_values())) == 0
            assert len(list(b.iter_referenced_values())) == 1
            assert list(b.iter_referenced_values())[0] is a

    def test_no_size(self) -> None:
        for ns in make_namespaces():
            partial_type = ns.get_class_for_type(
                IntType(ns, "partial_int_t", None, False)
            )
            with pytest.raises(ValueError):
                partial_type.cast(0)

    def test_cast_int(self) -> None:
        for ns in make_namespaces():
            assert ns.Int.cast(0).value == 0
            assert ns.Int.cast(1).value == 1
            assert ns.Int.cast("a").value == ord("a")
            assert ns.Int.cast(b"a").value == ord(b"a")
            assert ns.Int.cast(1.1).value == 1
            assert ns.Int.cast(1.5).value == 1
            assert ns.Int.cast(1.9).value == 1
            assert ns.Int.cast(-2.8).value == -2
            assert ns.Int.cast(0x7FFFFFFF).value == 0x7FFFFFFF
            assert ns.Int.cast(0xFFFFFFFF).value == -1
            assert ns.Int.cast(0xFFFFFFFE).value == -2
            assert ns.Int.cast(-1).value == -1
            assert ns.Int.cast(-2).value == -2
            with pytest.raises(TypeError):
                ns.Int.cast([])
            with pytest.raises(TypeError):
                ns.Int.cast("string")

    def test_cast_uint(self) -> None:
        for ns in make_namespaces():
            assert ns.UnsignedInt.cast(0).value == 0
            assert ns.UnsignedInt.cast(1).value == 1
            assert ns.UnsignedInt.cast("a").value == ord("a")
            assert ns.UnsignedInt.cast(b"a").value == ord(b"a")
            assert ns.UnsignedInt.cast(1.1).value == 1
            assert ns.UnsignedInt.cast(1.5).value == 1
            assert ns.UnsignedInt.cast(1.9).value == 1
            assert ns.UnsignedInt.cast(-2.8).value == 0xFFFFFFFE
            assert ns.UnsignedInt.cast(0x7FFFFFFF).value == 0x7FFFFFFF
            assert ns.UnsignedInt.cast(0xFFFFFFFF).value == 0xFFFFFFFF
            assert ns.UnsignedInt.cast(0xFFFFFFFE).value == 0xFFFFFFFE
            assert ns.UnsignedInt.cast(-1).value == 0xFFFFFFFF
            assert ns.UnsignedInt.cast(-2).value == 0xFFFFFFFE

    def test_underflow_overflow(self) -> None:
        unsigned_error = ".*cannot be represented by unsigned int of size.*"
        signed_error = ".*cannot be represented by signed int of size.*"
        for ns in make_namespaces():
            with pytest.raises(ValueError, match=signed_error):
                ns.Int(-2147483649)
            with pytest.raises(ValueError, match=signed_error):
                ns.Int(0x80000000)
            with pytest.raises(ValueError, match=signed_error):
                ns.Int(0x100000000)
            with pytest.raises(ValueError, match=unsigned_error):
                ns.UnsignedInt(-1)
            with pytest.raises(ValueError, match=unsigned_error):
                ns.UnsignedInt(0x100000000)
            with pytest.raises(ValueError, match=signed_error):
                ns.Char(128)
            with pytest.raises(ValueError, match=unsigned_error):
                ns.UnsignedChar(-1)

    def test_pack_integral_overflow(self) -> None:
        with pytest.raises(ValueError):
            _pack_integral_type(-1, 1, False, Endianness.LITTLE)

    def test_pack_int(self) -> None:
        def ntoh(b: bytes) -> bytes:
            if ns.arch.endianness == Endianness.LITTLE:
                return b[::-1]
            return b

        for ns in make_namespaces():
            assert ns.Int().pack() == ntoh(b"\x00\x00\x00\x00")
            assert ns.Int(1).pack() == ntoh(b"\x00\x00\x00\x01")
            assert ns.Int(2).pack() == ntoh(b"\x00\x00\x00\x02")
            assert ns.Int(0x7FFFFFFF).pack() == ntoh(b"\x7f\xff\xff\xff")
            assert ns.Int(-1).pack() == ntoh(b"\xff\xff\xff\xff")
            assert ns.Int(-2).pack() == ntoh(b"\xff\xff\xff\xfe")

            assert ns.UnsignedInt().pack() == ntoh(b"\x00\x00\x00\x00")
            assert ns.UnsignedInt(0).pack() == ntoh(b"\x00\x00\x00\x00")
            assert ns.UnsignedInt(1).pack() == ntoh(b"\x00\x00\x00\x01")
            assert ns.UnsignedInt(0xFFFFFFFF).pack() == ntoh(
                b"\xff\xff\xff\xff"
            )

    def test_unpack_int(self) -> None:
        for ns in make_namespaces():

            def ntoh(b: bytes) -> bytes:
                if ns.arch.endianness == Endianness.LITTLE:
                    return b[::-1]
                return b

            assert (
                ns.Int.unpack_from_buffer(ntoh(b"\x00\x00\x00\x00")).value == 0
            )
            assert (
                ns.Int.unpack_from_buffer(ntoh(b"\x00\x00\x00\x01")).value == 1
            )
            assert (
                ns.Int.unpack_from_buffer(ntoh(b"\x7f\xff\xff\xff")).value
                == 0x7FFFFFFF
            )
            assert (
                ns.Int.unpack_from_buffer(ntoh(b"\xff\xff\xff\xff")).value
                == -1
            )
            assert (
                ns.Int.unpack_from_buffer(ntoh(b"\xff\xff\xff\xfe")).value
                == -2
            )
            with pytest.raises(ValueError):
                ns.Int.unpack_from_buffer(b"")
            with pytest.raises(ValueError):
                ns.Int.unpack_from_buffer(b"123")
            with pytest.raises(ValueError):
                ns.Int.unpack_from_buffer(b"12345")

    def test_unpack_unsigned(self) -> None:
        for ns in make_namespaces():

            def ntoh(b: bytes) -> bytes:
                if ns.arch.endianness == Endianness.LITTLE:
                    return b[::-1]
                return b

            assert (
                ns.UnsignedInt.unpack_from_buffer(
                    ntoh(b"\x00\x00\x00\x00")
                ).value
                == 0
            )
            assert (
                ns.UnsignedInt.unpack_from_buffer(
                    ntoh(b"\x00\x00\x00\x01")
                ).value
                == 1
            )
            assert (
                ns.UnsignedInt.unpack_from_buffer(
                    ntoh(b"\x7f\xff\xff\xff")
                ).value
                == 0x7FFFFFFF
            )
            assert (
                ns.UnsignedInt.unpack_from_buffer(
                    ntoh(b"\xff\xff\xff\xff")
                ).value
                == 0xFFFFFFFF
            )
            assert (
                ns.UnsignedInt.unpack_from_buffer(
                    ntoh(b"\xff\xff\xff\xfe")
                ).value
                == 0xFFFFFFFE
            )
            with pytest.raises(ValueError):
                ns.UnsignedInt.unpack_from_buffer(b"")
            with pytest.raises(ValueError):
                ns.UnsignedInt.unpack_from_buffer(b"123")
            with pytest.raises(ValueError):
                ns.UnsignedInt.unpack_from_buffer(b"12345")
