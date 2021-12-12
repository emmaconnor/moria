

# Moria
[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/josconno/moria?sort=semver)](https://github.com/josconno/moria/tree/latest)
[![Build Status](https://github.com/josconno/moria/actions/workflows/python-tests.yml/badge.svg)](https://github.com/josconno/moria/actions/workflows/python-tests.yml)
[![PyPI version](https://badge.fury.io/py/moria-c.svg)](https://badge.fury.io/py/moria-c)
[![PyPI](https://img.shields.io/pypi/pyversions/moria-c.svg)](https://pypi.python.org/pypi/moria-c)


A library for interacting with in-memory C structures. With Moria, you can:

  - Extract C struct information from compiled binaries (using DWARF debug info)
  - Turn them into high-level python types
  - Manipulate values including nested structs, pointers, and arrays
  - Serialize into binary compatbile with the original program
  - Pack objects into a binary buffer
  - Automatically arrange string buffers, etc. in memory
  - Automatically compute pointer values in packed objects

## Why?

Data-only memory corruption exploits can involve reading and writing complex data structures in the target address space. Moria makes development of these types of exploits much easier. 

## Examples

Moria can manipulate complicated in-memory C datastructures using high-level python objects. For example, take the following C declaration for a linked list of user data:

```
struct user
{
    int id;
    char name[MAX_USERNAME_LEN];
    struct user *prev;
    struct user *next;
};
```

Moria can automatically extract the types, sizes, and offsets of the structure from binary compiled with debug info:

```
with open("uesrlist.bin", "rb") as binary:
    structs = DwarfParser(binary).parse()

user1 = structs.user()
user2 = structs.user()
```

You can set field values, including nested types and pointers that reference other objects, fields, or values:

```
user1.id = 1
user1.name = "alice"
user1.next = user2.ref()
user1.prev = user2.ref()

user2.id = 2
user2.name = "bob"
user2.next = user1.ref()
user2.prev = user1.ref()
```

Finally, you can pack your collection of objects into a byte array, automatically computing pointer values using a base address, ready to be injected into the target address space!

```
start_address = 0x560A61DF4000 # e.g. heap address
packed = namespace.pack_values(start_address, 0x1000, [user1, user2])
```

The result:

```
0000560a61df4000  01 00 00 00 61 6c 69 63  65 00 00 00 00 00 00 00  |....alice.......|
0000560a61df4010  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
0000560a61df4020  00 00 00 00 00 00 00 00  38 40 df 61 0a 56 00 00  |........8@.a.V..|
0000560a61df4030  38 40 df 61 0a 56 00 00  02 00 00 00 62 6f 62 00  |8@.a.V......bob.|
0000560a61df4040  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
0000560a61df4050  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
0000560a61df4060  00 40 df 61 0a 56 00 00  00 40 df 61 0a 56 00 00  |.@.a.V...@.a.V..|
```

### See Also

1. Connor, Richard J. III, *Improved Architectures for Secure Intra-process Isolation.* PhD diss., University of Tennessee, 2021.
https://trace.tennessee.edu/utk_graddiss/6533
2. [proc/mem attack](https://github.com/josconno/proc-mem-attack)
