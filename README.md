# moria
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

