# Semantic Embedding Sync — Code Review Notes

Copyright 2026 ITTH GmbH & Co. KG

## Problem

`rclsem_embed.py` only handles initial population of ChromaDB. It does not detect
modified or deleted documents. Re-running it skips all existing segment IDs,
leaving stale embeddings in place.

## Affected File

`src/semantic/rclsem_embed.py` — `update_embeddings()` function (lines 37-88)

## Current Behavior

- Segments stored with ID `rcludi+index`, no metadata
- Check at line 76-79: if segment ID exists in ChromaDB, skip
- No signature comparison for modifications
- No cleanup pass for deletions

## Proposed Changes

### 1. Store doc signature as metadata on each segment

Current (line 85-88):
```python
collection.add(ids=ids, embeddings=embeddings)
```

Proposed:
```python
collection.add(
    ids=ids,
    embeddings=embeddings,
    metadatas=[{"rcludi": rcludi, "sig": doc.sig} for _ in ids],
)
```

`doc.sig` is already exposed by the Recoll Python API (`pyrecoll.cpp:434-435`)
and is used internally by Recoll for its own up-to-date checks (typically
mtime+size based).

### 2. Detect modifications via signature comparison

Replace the simple "already there? skip" check (lines 74-79) with signature
comparison:

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

On first changed segment detected, all old segments for that document are purged
and re-embedding starts fresh.

### 3. Delete orphaned documents after embedding loop

Add a cleanup pass after the main embedding loop:

```python
# Collect all rcludi values currently in the Recoll index
current_udis = set()
for doc in query:
    current_udis.add(doc.rcludi)

# Find ChromaDB entries whose rcludi is no longer in the index
all_chroma = collection.get(include=["metadatas"])
orphaned_ids = []
for seg_id, meta in zip(all_chroma['ids'], all_chroma['metadatas']):
    if meta.get('rcludi') not in current_udis:
        orphaned_ids.append(seg_id)

if orphaned_ids:
    for i in range(0, len(orphaned_ids), 500):
        collection.delete(ids=orphaned_ids[i:i+500])
```

## Summary

| Change          | Mechanism                                         | Key field          |
|-----------------|---------------------------------------------------|--------------------|
| New docs        | Existing logic (check ID, add if missing)         | `rcludi`           |
| Modified docs   | Compare `doc.sig` stored as ChromaDB metadata     | `doc.sig`          |
| Deleted docs    | Post-loop cleanup: ChromaDB udis not in index     | `rcludi` metadata  |

---

## Performance Bottlenecks

### Bottleneck 1: One-by-one ollama calls (highest impact)

`rclsem_embed.py:82` calls `get_embedding()` per segment, which issues one HTTP
round-trip to ollama each time (`rclsem_common.py:36`):

```python
# Current: N HTTP calls per slice (up to 100)
for i in range(len(sentslice)-1):
    embeddings.append(get_embedding(sentslice[i], embedmodel))
```

`ollama.embed()` already supports batch input — a list of strings returns all
embeddings in one call. With a remote ollama instance, this eliminates up to 99
network round-trips per 100-segment slice. The ollama server can also
parallelize embedding computation internally on batch input.

Proposed `get_embedding()` change in `rclsem_common.py`:
```python
def get_embeddings_batch(texts, embedmodel):
    response = ollama.embed(model=embedmodel, input=texts)
    return response['embeddings']
```

Proposed call site in `rclsem_embed.py`:
```python
texts_to_embed = [sentslice[i] for i in new_indices]
embeddings = get_embeddings_batch(texts_to_embed, embedmodel)
```

### Bottleneck 2: One-by-one ChromaDB existence checks

`rclsem_embed.py:76` queries ChromaDB per segment:

```python
# Current: N DB queries per slice
for i in range(len(sentslice)-1):
    results = collection.get(ids=[segid])
```

ChromaDB `get()` accepts a list of IDs. Check the entire slice in one call:

```python
# Proposed: 1 DB query per slice
all_ids = [rcludi + "+" + str(sentidx + i) for i in range(len(sentslice))]
existing = set(collection.get(ids=all_ids)['ids'])
new_indices = [i for i, sid in enumerate(all_ids) if sid not in existing]
```

### Bottleneck 3: Off-by-one drops last segment per slice

`rclsem_embed.py:70` — `range(len(sentslice)-1)` silently skips the last
segment of every slice. Likely a bug (perhaps intended to avoid a trailing
empty segment from `dotbreak`, but that should be handled in `dotbreak` itself).

```python
# Current: drops last segment
for i in range(len(sentslice)-1):

# Fix:
for i in range(len(sentslice)):
```

### Performance impact summary

| Bottleneck | Location | Current | Proposed | Impact |
|---|---|---|---|---|
| Ollama calls | `embed.py:82` / `common.py:36` | N HTTP calls/slice | 1 batch call/slice | ~100x fewer round-trips |
| ChromaDB checks | `embed.py:76` | N DB queries/slice | 1 batch query/slice | ~100x fewer DB queries |
| Off-by-one | `embed.py:70` | Last segment dropped | All segments processed | Data completeness |

---

## Migration Note

Existing ChromaDB databases created before these changes have no metadata on
segments. A one-time full re-embed (delete `chromadb/` directory and re-run) is
required after applying these changes.

## References

- `src/semantic/rclsem_embed.py` — embedding logic
- `src/semantic/rclsem_common.py` — ChromaDB/ollama init, `get_embedding()`
- `src/rcldb/rcldoc.h:110-114` — `doc.sig` definition
- `src/python/recoll/pyrecoll.cpp:434-435` — `doc.sig` Python API exposure
