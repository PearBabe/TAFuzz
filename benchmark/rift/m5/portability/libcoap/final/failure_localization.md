# Read-only failure localization

No second large run was performed.

The `recipes` implementation orders its first operations as follows:

```text
index_for(plan)
OutputBundleStager(output_dir)
semantic_index_json(index) -> encoded_json(...)
bundle.write("semantic_index.json", payload)
model overlay
predicate occurrences
AP binding / graph / cones
frontier
recipes / replay obligations
certificates
```

Filesystem timestamps show that the command started at approximately
`14:08:02` and created the result directory at `14:08:12`. Because the stager
is constructed only after `index_for(plan)` returns, raw indexing completed in
roughly the first ten seconds. During the run, inspections found no staged
artifact file. At failure (`14:14:59`), the stager removed its private
directory and left the public result directory empty.

The last definitely completed point is therefore **in-memory semantic index
construction**. The failure occurred before any model, occurrence, binding,
graph, cone, frontier, recipe, replay-obligation, or certificate artifact was
published. Given the monotonic memory growth to 12,211,160 KiB, the empty first
artifact, and the code order, the strongest current localization is
`semantic_index_json(index)` / `encoded_json(...)` materialization before the
first `semantic_index.json` publication. It cannot be narrowed between JSON
object construction, string encoding, hashing, and the first staged write
without phase tracing; the allocation signature makes the first two the most
likely.

Available measurements are whole-command only because `RIFT_RESOURCE_TRACE`
was not enabled:

```text
wall_seconds=417.76
user_seconds=361.95
system_seconds=22.19
peak_rss_kib=12211160
public result files=0
certificate files=0
```

The next immutable-snapshot retry should enable `RIFT_RESOURCE_TRACE=1`. It
should not be presented as a completed M5 run unless the first artifact,
downstream stages, and detached certificate all succeed under the registered
resource gate.
