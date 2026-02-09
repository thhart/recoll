# Changelog

## 2026-02-09

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
