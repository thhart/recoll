#!/bin/sh
# Copyright (C) 2025 J.F.Dockes
#
# License: GPL 2.1
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2.1 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

# Initialize the semantic search Python venv.
# Creates the venv and installs chromadb + ollama Python packages.
# Scripts are installed separately at /usr/share/recoll-semantic/.
# Usage: initsemenv.sh <venvdir> [pull_model]
#   pull_model: "true" (default) or "false" — whether to pull the embedding model
# Set OLLAMA_HOST in the environment to use a remote ollama server.
# Copyright 2026 ITTH GmbH & Co. KG


fatal()
{
    echo $* 1>&2
    exit 1
}
usage()
{
    fatal "Usage: initsemenv.sh <venvdir> [true|false]"
}

test $# -ge 1 || usage
venvdir=$1
pull_model=${2:-true}

echo "recoll-semantic: creating Python venv at $venvdir ..."
mkdir -p "$venvdir" || exit 1
python3 -m venv "$venvdir" || exit 1
. "$venvdir"/bin/activate
echo "recoll-semantic: installing Python packages (this may take a few minutes) ..."
python3 -m pip install --quiet chromadb==1.5.0 ollama
deactivate

# Install the recoll Python module into the venv so scripts can import it
recollmod=`echo 'from recoll import recoll; print(recoll.__file__)' | python3 2>/dev/null`
if test -n "$recollmod"; then
    rclmoddir=`dirname $recollmod`
    cp -rp "$rclmoddir" "$venvdir"/lib/python*/site-packages
fi

if test "$pull_model" = "true"; then
    ol=`which ollama`
    if test -z "$ol"; then
        echo "recoll-semantic: installing ollama ..."
        curl -fsSL https://ollama.com/install.sh | sh
    fi
    echo "recoll-semantic: pulling embedding model (this may take several minutes) ..."
    ollama pull nomic-embed-text
else
    echo "recoll-semantic: skipping model pull (configured to skip or using remote ollama)"
fi
