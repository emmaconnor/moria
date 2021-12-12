import pytest
from tests.helpers import make_namespace, make_namespaces, amd64_namespace
from moria.basetypes import IntType, PointerType, StructField, StructType


class TestType:
    def test_abstract_methods(self):
        for ns in make_namespaces():
            int_t = ns.Int.type
            with pytest.raises(NotImplementedError):
                super(IntType, int_t).name
            with pytest.raises(NotImplementedError):
                super(IntType, int_t).size
            with pytest.raises(NotImplementedError):
                super(IntType, int_t).__hash__()
            with pytest.raises(NotImplementedError):
                super(IntType, int_t).__eq__(int_t)


class TestIntType:
    def test_unsized_int(self):
        for ns in make_namespaces():
            partial_int_type = IntType(ns, 'partial_int_t', None, False)
            with pytest.raises(ValueError):
                partial_int_type.max

    def test_str_repr(self):
        for ns in make_namespaces():
            assert(str(ns.Int.type) == 'int')
            assert(repr(ns.Int.type) == '<IntType 4 bytes, signed>')

            assert(str(ns.Char.type) == 'char')
            assert(repr(ns.Char.type) == '<IntType 1 byte, signed>')


class TestArrayType:
    def test_name(self):
        for ns in make_namespaces():
            array_t = ns.array(ns.Int, 5).type
            assert array_t.name == 'int[5]'
            assert str(array_t) == 'int[5]'
            assert repr(array_t) == '<ArrayType of 5 int>'

    def test_eq(self):
        for ns in make_namespaces():
            int_arr = ns.array(ns.Int, 5).type
            int_arr2 = ns.array(ns.Int, 5).type
            int8_arr = ns.array(ns.Int8, 5).type
            char_arr = ns.array(ns.Char, 5).type
            char_2_arr = ns.array(ns.Char, 2).type
            assert int_arr == int_arr2
            assert hash(int_arr) == hash(int_arr2)
            assert int8_arr == char_arr
            assert hash(int8_arr) == hash(char_arr)
            assert int_arr != char_arr
            assert char_2_arr != int_arr
            assert char_2_arr != char_arr

    def test_partial(self):
        for ns in make_namespaces():
            partial_int_type = IntType(ns, 'partial_int_t', None, False)
            array_t = ns.array(ns.get_class_for_type(partial_int_type), 5).type
            assert array_t.size is None


class TestPointerType:
    def test_size(self):
        for ns in make_namespaces():
            void_pointer = ns.VoidPointer.type
            assert void_pointer.size == ns.arch.pointer_size

            with pytest.raises(ValueError):
                PointerType(void_pointer, 1)

    def test_hash_eq(self):
        for ns in make_namespaces():
            void_pointer = ns.VoidPointer.type
            assert (void_pointer) == (
                PointerType((IntType(ns, 'void', None, False))))
            assert hash(void_pointer) == hash(
                PointerType((IntType(ns, 'void', None, False))))

    def test_repr(self):
        for ns in make_namespaces():
            void_pointer = ns.VoidPointer.type
            assert repr(void_pointer) == '<PointerType to void>'
            assert repr(void_pointer.get_pointer_type()) == '<PointerType to void*>'
            assert repr(ns.Char.type.get_pointer_type()) == '<PointerType to char>'


class TestStructField:
    def test_repr(self):
        for ns in make_namespaces():
            field = StructField(ns, 0, ns.Int.type, "i")
            assert repr(field) == "<StructField int i>"

    def test_hash_eq(self):
        for ns in make_namespaces():
            field1 = StructField(ns, 0, ns.Int.type, "i")
            field2 = StructField(ns, 0, ns.Int.type, "i")
            field_j = StructField(ns, 0, ns.Int.type, "j")
            field_offset = StructField(ns, 4, ns.Int.type, "i")
            field_char = StructField(ns, 0, ns.Char.type, "i")
            assert hash(field1) == hash(field2)
            assert field1 == field2
            assert field1 != field_j
            assert field1 != field_offset
            assert field1 != field_char


class TestStructType:
    def test_size(self):
        for ns in make_namespaces():
            partial_type = StructType(ns, 'struct partial')
            assert partial_type.size is None

            partial_int_type = IntType(ns, 'partial_int_t', None, False)
            partial_field_struct = StructType(ns, 'struct pfs')
            partial_field_struct.add_field(StructField(ns, 0, partial_int_type, 'partial'))
            assert partial_field_struct.size is None

    def test_eq(self):
        for ns in make_namespaces():
            struct_type = StructType(ns, 'struct test')
            struct_type.add_field(StructField(ns, 0, ns.UInt32.type, 'i'))

            struct_type2 = StructType(ns, 'struct test')
            struct_type2.add_field(StructField(ns, 0, ns.UInt32.type, 'i'))

            assert struct_type is not struct_type2
            assert hash(struct_type) == hash(struct_type2)
            assert struct_type == struct_type2

    def test_reprs(self):
        for ns in make_namespaces():
            child_type = StructType(ns, 'child')
            child_type.add_field(StructField(ns, 0, ns.UInt32.type, 'j'))
            child_type.add_field(StructField(ns, 4, ns.array(ns.Char, 16).type, 'name'))
            assert repr(child_type) == "<StructType child: uint32_t j, char[16] name>"

            struct_type = StructType(ns, 'parent')
            struct_type.add_field(StructField(ns, 0, ns.UInt32.type, 'i'))
            struct_type.add_field(StructField(ns, 4, child_type, 'child'))

            assert struct_type.pretty_string() == '\n'.join([
                'struct parent {',
                '  uint32_t i;',
                '  struct child {',
                '    uint32_t j;',
                '    char[16] name;',
                '  };',
                '};',
            ])
