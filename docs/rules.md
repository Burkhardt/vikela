# Vikela mutation rules

The logical IDs agree with RaiGuard. Pylint exposes native IDs and symbols:

| Logical ID | Pylint ID | Symbol |
|---|---|---|
| RAI011 | W9011 | vikela-full-snapshot-write |
| RAI012 | W9012 | vikela-protected-attribute |
| RAI021 | E9021 | vikela-test-configuration |
| RAI022 | E9022 | vikela-test-pit-location |
| RAI023 | E9023 | vikela-pit-directory |

## RAI023

Reports recognizable Pit constructors passed strings, `pathlib.Path`, file
objects or `.pit` filenames instead of an Inqaba `InqPath` directory.
`Pit.open` also accepts a bare cloud Pit name. The CLI may accept a filename
and resolve it before constructing a Pit. Unknown dynamic argument types and
cross-module aliases cannot be proven safe by this static check. RAI023 cannot
be disabled through Vikela's CLI or project configuration.

## RAI021

Reports recognizable configuration substitutions, including writes to a
`RAIkeep.json5` path, configuration-related environment overrides, synthetic
cloud mappings, and mocked configuration loaders. It is an error: tests must
use the actual `~/.config/RAIkeep.json5` and its configured TestCloud.
The check is static and cannot prove the behavior of dynamic code or resolve
all aliases. Review findings in production configuration tools in context.
RAI021 cannot be disabled through Vikela's CLI or project configuration.

## RAI022

Reports recognizable Pit openings and `.pit` or `.pit.tmp` writes rooted in
system temporary locations or pytest's temporary-path fixtures. Test Pits belong
in a run-owned directory on the configured TestCloud; exported JSON copies may
be written to a temporary directory. The check tracks direct local aliases but
also checks literal Python `-c` subprocess source. It cannot determine every
dynamic path or cross-module helper. In particular, no
finding for an unknown path does not prove that the path is inside TestCloud.
RAI022 cannot be disabled through Vikela's CLI or project configuration.

## RAI011

Warn when a detached full projection is submitted through a resolved JsonPit
`add`, or a live handle has a provably different owner or retired lifetime.
Recognized origins include historical queries, item copies, to_dict/deepcopy,
aliases, collection elements, and bounded source-helper summaries.

```python
snapshot = pit.get_at("Ego", timestamp)
pit.add(snapshot)  # RAI011: a historical projection is not an intended delta
```

Prefer ordinary live operations:

```python
item = pit["Ego"]
item["Status"] = "Doing"
# Or group several intended fields:
item.set_property({"Status": "Doing", "Location": "Main stage"})
```

A fresh PitItem containing explicit intended fields is also supported. Adding an
owned live handle back is a supported boundary flush, although normal tracked
edits do not require that call. Genuine replay uses add_historical; do not use it
to bypass client guards.

## RAI012

Id, Modified, and Deleted are lifecycle attributes, not arbitrary business fields.
Direct property/indexer assignments and explicit mutation/deletion payloads must
not alter them. A matching Id assertion in a patch is allowed by the runtime.
Use rename_id/delete_item for lifecycle changes. The diagnostic names the protected
attribute and recommends the object-oriented APIs.

## Scope and uncertainty

Analysis resolves JsonPit imports (including aliases), explicit annotations, and
propagated values. It does not treat objects named `pit` as JsonPit objects.
Source is parsed, never executed. Unresolved dynamic imports, monkey-patching,
reflection, cross-module helper bodies, and arbitrary callbacks are not proven.
Helper analysis is bounded to four calls in the inspected source. Collection
tracking covers literal collections and directly propagated append/add/extend
operations; it does not model arbitrary iterators or custom containers.
Branch joins keep only facts agreed by continuing paths. Loop effects are bounded
and joined with the zero-iteration path. Unknown values do not become proven
violations merely because the method is named add. Static analysis cannot prove
all dynamic program behavior; JsonPit runtime guards remain authoritative.

These warnings describe intent/provenance hazards; they do not claim every live
read/edit/add sequence republishes a full snapshot. Remove/del on a tracked live
handle can emit a tombstone and is supported. Detached sparse payload omission is
not a tombstone. Rewriting one into the other requires knowing developer intent.

## Suggestions and fixes

Findings contain rule, severity, path, line, column, reason, suggestion,
documentation URL, optional notebook cell, and fix_available. Version 4.6.3 marks
all fixes unavailable: --fix and --qondisa are accepted but perform no speculative
rewrites. File inspection never edits source or executes notebook cells.
