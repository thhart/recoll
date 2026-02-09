#!/bin/sh
# recollsemantic — manage the recoll semantic search subsystem.
# Copyright 2026 ITTH GmbH & Co. KG
set -e

# When installed, scripts live in /usr/share/recoll-semantic/.
# When run from the source tree, they're alongside this script.
SCRIPTDIR=$(dirname "$(readlink -f "$0")")
if test -d /usr/share/recoll-semantic && ! test -f "$SCRIPTDIR/rclsem_embed.py"; then
    SCRIPTDIR=/usr/share/recoll-semantic
fi

usage() {
    cat >&2 <<EOF
Usage: recollsemantic [-c confdir] <command>

Commands:
  init    Create/recreate the Python venv and pull the embedding model
  embed   Update semantic embeddings from the recoll index
  query   Interactive semantic query shell

Options:
  -c confdir   Recoll configuration directory (default: ~/.recoll)
EOF
    exit 1
}

# Parse global options
confdir=""
while getopts "c:" opt; do
    case $opt in
        c) confdir="$OPTARG" ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))

test $# -ge 1 || usage
cmd="$1"
shift

# Resolve sem_venv from recoll config
if test -z "$confdir"; then
    confdir="${RECOLL_CONFDIR:-$HOME/.recoll}"
fi

sem_venv=""
if test -f "$confdir/recoll.conf"; then
    sem_venv=$(sed -n 's/^sem_venv[[:space:]]*=[[:space:]]*//p' "$confdir/recoll.conf" | tail -1)
fi

case "$cmd" in
    init)
        if test -z "$sem_venv"; then
            sem_venv=/var/lib/recoll-semantic/venv
            echo "sem_venv not set in $confdir/recoll.conf, using default: $sem_venv"
        fi
        "$SCRIPTDIR/initsemenv.sh" "$sem_venv" "$@"
        echo ""
        echo "Done. Ensure your $confdir/recoll.conf contains:"
        echo "  sem_venv = $sem_venv"
        ;;
    embed)
        if test -z "$sem_venv"; then
            echo "Error: sem_venv not set in $confdir/recoll.conf" >&2
            exit 1
        fi
        exec "$sem_venv/bin/python3" "$SCRIPTDIR/rclsem_embed.py" -c "$confdir" "$@"
        ;;
    query)
        if test -z "$sem_venv"; then
            echo "Error: sem_venv not set in $confdir/recoll.conf" >&2
            exit 1
        fi
        exec "$sem_venv/bin/python3" "$SCRIPTDIR/rclsem_query.py" -c "$confdir" "$@"
        ;;
    *)
        echo "Unknown command: $cmd" >&2
        usage
        ;;
esac
