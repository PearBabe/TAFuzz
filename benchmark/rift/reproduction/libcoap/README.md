# libcoap Clang/LLVM 18 reproduction

This directory freezes the pre-RIFT whole-program compilation baseline for
libcoap commit `94bacc8939dd6711169cd2332a002a361ec62531`.

Run from the TAFuzz root:

```bash
python3 benchmark/rift/reproduction/libcoap/reproduce_clang18.py \
  --output benchmark/rift/reproduction/libcoap/observed_results.json
```

The script uses one fixed, guarded directory below `/tmp` for all repetitions.
This keeps DWARF build paths stable while preventing accidental deletion of a
workspace directory.  DTLS is explicitly disabled because the frozen checkout
does not contain the optional `ext/tinydtls` submodule.  Tests are disabled in
this compilation-only baseline because CUnit is not installed; this is not a
runtime libcoap validation.

Acceptance requires three identical compile-database, static-archive, and
linked-bitcode hashes and a successful LLVM 18 MemorySSA construction.
