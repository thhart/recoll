# Semantic Embedding — Review Notes

Copyright 2026 ITTH GmbH & Co. KG

---

## Implemented Optimizations

All implemented on `semantic` branch, tested and working.

### Batch ollama calls — DONE
`rclsem_common.py`: Added `get_embeddings_batch()` — single HTTP call per batch
instead of per-segment. Eliminates up to 99 network round-trips per 100-segment
slice, especially impactful with remote ollama.

### Batch ChromaDB existence checks — DONE
`rclsem_embed.py`: One `collection.get(ids=[...])` per slice instead of per
segment. ~100x fewer DB queries per slice.

### Cross-document batching — DONE
`rclsem_embed.py`: Segments accumulate across document boundaries into a shared
buffer (`BATCH_SIZE=100`). Flushes to ollama when full, ensuring consistent GPU
utilization regardless of individual document sizes.

### Early skip for fully-embedded documents — DONE
`rclsem_embed.py`: `doc_fully_embedded()` checks first+last segment ID in
ChromaDB. If both exist, entire document is skipped. Makes re-runs near-instant
for unchanged indexes.

### Off-by-one fix — DONE
`rclsem_embed.py`: `range(len(sentslice))` instead of `range(len(sentslice)-1)`.
Last segment of each slice is no longer silently dropped.

### Progress output — DONE
`rclsem_embed.py`: Single overwriting line per file: `[N/total] filename pct%`
with `skipped` for already-embedded docs. Final summary: `Done: N documents
processed, M skipped.`

### Debian packaging for semantic — DONE
`packaging/debian/debian/control`: Added `libjsoncpp-dev (>= 1.9.0)` to
Build-Depends.
`packaging/debian/debian/rules`: Added `-Dsemantic=true` to meson configure.

---

## Pending — Sync Logic (not yet implemented)

### 1. Store doc signature as metadata on each segment

Store `doc.sig` and `rcludi` as ChromaDB metadata on each segment to enable
modification detection:

```python
collection.add(
    ids=ids,
    embeddings=embeddings,
    metadatas=[{"rcludi": rcludi, "sig": doc.sig} for _ in ids],
)
```

`doc.sig` is exposed by the Recoll Python API (`pyrecoll.cpp:434-435`) and is
used internally by Recoll for up-to-date checks (typically mtime+size based).

### 2. Detect modifications via signature comparison

Replace the simple "already there? skip" with signature comparison. On first
changed segment detected, purge all old segments for that document and re-embed:

```python
segid = rcludi + "+" + str(idx)
results = collection.get(ids=[segid], include=["metadatas"])
if results['ids']:
    stored_sig = results['metadatas'][0].get('sig', '')
    if stored_sig == doc.sig:
        continue  # unchanged, skip
    # Changed — delete all old segments for this doc, re-embed
    old_segs = collection.get(where={"rcludi": rcludi})
    if old_segs['ids']:
        collection.delete(ids=old_segs['ids'])
    break  # restart this doc's segments from scratch
```

### 3. Delete orphaned documents after embedding loop

Cleanup pass: find ChromaDB entries whose `rcludi` is no longer in the Recoll
index:

```python
current_udis = set()
for doc in query:
    current_udis.add(doc.rcludi)

all_chroma = collection.get(include=["metadatas"])
orphaned_ids = []
for seg_id, meta in zip(all_chroma['ids'], all_chroma['metadatas']):
    if meta.get('rcludi') not in current_udis:
        orphaned_ids.append(seg_id)

if orphaned_ids:
    for i in range(0, len(orphaned_ids), 500):
        collection.delete(ids=orphaned_ids[i:i+500])
```

### Sync summary

| Change          | Mechanism                                         | Key field          |
|-----------------|---------------------------------------------------|--------------------|
| New docs        | Existing logic (check ID, add if missing)         | `rcludi`           |
| Modified docs   | Compare `doc.sig` stored as ChromaDB metadata     | `doc.sig`          |
| Deleted docs    | Post-loop cleanup: ChromaDB udis not in index     | `rcludi` metadata  |

---

## Pending — Further Optimizations (not yet implemented)

### Pipeline with threading

Use `ThreadPoolExecutor` with producer-consumer pattern: one thread segments and
checks ChromaDB, another calls ollama, a third stores results. Python's GIL
doesn't matter since the bottleneck is network I/O. Overlaps the three wait
periods. Most impactful with remote ollama.

---

## Migration Note

Existing ChromaDB databases created before the sync changes (pending) have no
metadata on segments. A one-time full re-embed (delete `chromadb/` directory and
re-run) will be required after implementing the sync logic.

## References

- `src/semantic/rclsem_embed.py` — embedding logic
- `src/semantic/rclsem_common.py` — ChromaDB/ollama init, `get_embedding()`
- `src/rcldb/rcldoc.h:110-114` — `doc.sig` definition
- `src/python/recoll/pyrecoll.cpp:434-435` — `doc.sig` Python API exposure
- `src/query/docseqsem.cpp` — C++ semantic integration, calls `rclsem_talk.py`
- `packaging/debian/debian/{control,rules}` — Debian packaging
