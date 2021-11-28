# moria
A library for interacting with in-memory C structures. With Moria, you can:

  - Extract C struct information from compiled binaries (using DWARF debug info)
  - Turn them into high-level python types
  - Manipulate fields including nested structs, pointers, and arrays
  - Serialize into binary compatbile with the original program
  - Pack objects into a binary buffer
  - Automatically compute pointer values of packed objects
