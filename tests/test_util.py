from moria.util import hexdump, SortedList
import pytest


def test_hexdump(capfd: pytest.CaptureFixture):
    hexdump(b'hello\x00\x01\xff', start_address=0x10)
    out, err = capfd.readouterr()
    assert err == ''
    assert out == "0000000000000010  68 65 6c 6c 6f 00 01 ff                           |hello...|\n"


def test_sorted_list():
    def comp_ints(x: int, y: int) -> int:
        return x - y
    nums = SortedList(key=comp_ints)
    nums_to_insert = [5, 4, 2, 5123123, -5123, -51, 0, 4, 1]
    for n in nums_to_insert:
        nums.insert(n)
    assert list(nums) == sorted(nums_to_insert)
