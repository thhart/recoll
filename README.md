# Recoll — with Semantic Search

Recoll is a desktop full-text search tool. It finds keywords inside
documents as well as file names.

* Versions are available for Linux and MS Windows.
* A WEB front-end with preview and download features can replace or
  supplement the GUI for remote use.
* It can search most document formats. You may need external applications
  for text extraction.
* It can reach any storage place: files, archive members, email
  attachments, transparently handling decompression.
* One click will open the document inside a native editor or display an
  even quicker text preview.
* The software is free, open source, and licensed under the GPL.

For more detail, see the [features page](https://www.recoll.org/pages/features.html) or
the [documentation](https://www.recoll.org/pages/documentation.html).

This is a fork of [Recoll](https://framagit.org/medoc92/recoll) adding
optimized semantic (vector embedding) search support.

## What this fork adds

The `semantic` branch enables semantic search as described in the
[upstream documentation](https://www.recoll.org/pages/recoll-semantic.html),
with the following additions:

- **Debian packaging** with `-Dsemantic=true` enabled and `libjsoncpp-dev`
  build dependency
- **Batch ollama embedding** — single HTTP call per 100 segments instead of
  per-segment, critical for remote GPU workers
- **Batch ChromaDB checks** — one query per slice instead of per segment
- **Cross-document batching** — segments accumulate across documents for
  consistent GPU utilization
- **Early skip** for already-embedded documents (checks first+last segment)
- **Progress reporting** — `[N/total] filename pct%` with skip summary
- **Off-by-one fix** — last segment per slice was silently dropped

## Installing from APT

Pre-built `.deb` packages for Ubuntu 24.04 (Noble) are published via GitHub
Pages:

```bash
# Add the repository signing key
curl -fsSL https://thhart.github.io/recoll/KEY.gpg \
  | sudo tee /etc/apt/keyrings/recoll-semantic.gpg > /dev/null

# Add the repository
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/recoll-semantic.gpg] https://thhart.github.io/recoll noble main" \
  | sudo tee /etc/apt/sources.list.d/recoll-semantic.list > /dev/null

# Install
sudo apt update && sudo apt install recoll-semantic
```

Packages are rebuilt automatically on every push to the `semantic` branch.

## Building the .deb

```bash
cd src
./makesrcdist.sh -t do_it

cd /tmp
cp recoll-1.43.12.tar.gz recoll_1.43.12.orig.tar.gz
tar xzf recoll_1.43.12.orig.tar.gz
cp -rp /path/to/recoll/packaging/debian/debian/ recoll-1.43.12/debian/
cd recoll-1.43.12
dpkg-buildpackage -us -uc -b
```

## Setup after install

```bash
# Initialize the semantic venv (installs chromadb, ollama, pulls model)
cd src/semantic
./initsemenv.sh /home/<user>/.recoll/semantic

# Add to ~/.recoll/recoll.conf
sem_venv = /home/<user>/.recoll/semantic

# Build embeddings
~/.recoll/semantic/bin/python3 ~/.recoll/semantic/rclsem_embed.py
```

For remote ollama, set `OLLAMA_HOST` before running:

```bash
OLLAMA_HOST=http://gpu-server:11434 ~/.recoll/semantic/bin/python3 ~/.recoll/semantic/rclsem_embed.py
```

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sem_venv` | (required) | Path to the semantic Python venv |
| `sem_rclquery` | `mime:*` | Restrict which documents get embedded |
| `sem_chromadbdir` | `~/.recoll/chromadb` | ChromaDB storage location |
| `sem_embedmodel` | `nomic-embed-text` | Ollama embedding model |
| `sem_embedsegsize` | `1000` | Target segment size in characters |

## Upstream

Upstream by J.F. Dockes: [framagit.org/medoc92/recoll](https://framagit.org/medoc92/recoll)

- [Building from source](https://www.recoll.org/usermanual/usermanual.html#RCL.INSTALL.BUILDING)
- [Semantic search documentation](https://www.recoll.org/pages/recoll-semantic.html)
