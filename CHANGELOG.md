# Changelog

## 2026-02-09

- Interactive deb install via debconf: prompts for ollama server URL
  and whether to download the embedding model during install
- Add `sem_ollama_host` config parameter: configure remote ollama
  server URL from `recoll.conf` (no more manual `OLLAMA_HOST` env var)
- Add `postindexcmd` config parameter to recollindex: runs a shell
  command after successful batch indexing (e.g. to update embeddings)
- Pin chromadb==1.5.0 in initsemenv.sh to prevent DB format breakage
- Integrate semantic init into deb package: scripts installed to
  `/usr/share/recoll-semantic/`, venv auto-created at
  `/var/lib/recoll-semantic/venv` via postinst
- C++ now finds scripts from installed datadir, sets PYTHONPATH for
  peer modules and recoll filters
- Simplified `initsemenv.sh`: only creates venv and installs pip packages
  (scripts and filter libs handled by package install + PYTHONPATH)
- Added `_sempath.py` for Python path setup in installed layout
- Added `python3-venv`, `python3-pip`, `python3-recoll`, `curl` as
  dependencies of `recoll-semantic`
- Add GitHub Pages APT repository: workflow publishes signed `.deb` packages
  to `https://thhart.github.io/recoll` after each push to `semantic`
- Rename deb metapackage to `recoll-semantic` (conflicts/replaces upstream `recoll`)
- Add installation-from-APT instructions to README
