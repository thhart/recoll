#!/usr/bin/env python3
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


import sys
import os
import getopt
from hashlib import md5

import chromadb
import ollama

from recoll import recoll
import rclconfig

from rclsem_segment import dotbreak
from slicelist import slicelist
from rclsem_common import deb, common_init, get_embedding, get_embeddings_batch, get_rclconfig

BATCH_SIZE = 100

def flush_batch(collection, batch_ids, batch_texts, embedmodel):
    """Embed and store a batch of segments across documents in one ollama call."""
    if not batch_ids:
        return
    embeddings = get_embeddings_batch(batch_texts, embedmodel)
    collection.add(ids=batch_ids, embeddings=embeddings)


def doc_fully_embedded(collection, rcludi, segcount):
    """Quick check: if first and last segment exist, assume doc is fully embedded."""
    check_ids = [rcludi + "+0"]
    if segcount > 1:
        check_ids.append(rcludi + "+" + str(segcount - 1))
    result = collection.get(ids=check_ids)
    return len(result['ids']) == len(check_ids)


def update_embeddings(rcldb, collection, embedmodel, embedsegsize):

    # It is possible to configure a restricting recoll query instead of processing the whole index
    rclconf = get_rclconfig()
    rclquery = rclconf.getConfParam("sem_rclquery")
    if not rclquery:
        rclquery = "mime:*"

    query = rcldb.query()
    query.execute(rclquery, fetchtext=True)

    # Count total docs for progress reporting
    doccount = query.rowcount if hasattr(query, 'rowcount') else -1

    # Cross-document batch buffer
    batch_ids = []
    batch_texts = []

    docnum = 0
    skipped = 0
    for doc in query:
        docnum += 1
        # Each segment sent for embedding gets the doc file name and title as prefix to maintain
        # global context.
        prefix = os.path.splitext(doc.filename)[0] + ": " + doc.title
        # Break up the document text in segments for embedding.
        sentences = dotbreak(doc.text, embedsegsize, prefix=prefix)
        # Doc identifier
        rcludi = doc.rcludi
        segcount = len(sentences)

        if segcount == 0:
            continue

        # Early skip: if first and last segments exist, doc is already fully embedded
        if doc_fully_embedded(collection, rcludi, segcount):
            skipped += 1
            progress = f"[{docnum}"
            if doccount > 0:
                progress += f"/{doccount}"
            progress += f"] {doc.filename} skipped"
            print(f"\r{progress:<79}", end="", file=sys.stderr, flush=True)
            continue

        # Collect new segments, batch-checking ChromaDB per slice
        segsdone = 0
        for sentidx, sentslice in slicelist(sentences, BATCH_SIZE):
            # Build all segment IDs for this slice and batch-check ChromaDB
            all_segids = [rcludi + "+" + str(sentidx + i) for i in range(len(sentslice))]
            existing = set(collection.get(ids=all_segids)['ids'])

            for i, segid in enumerate(all_segids):
                if segid in existing:
                    continue
                batch_ids.append(segid)
                batch_texts.append(sentslice[i])

                # Flush when cross-document batch is full
                if len(batch_ids) >= BATCH_SIZE:
                    flush_batch(collection, batch_ids, batch_texts, embedmodel)
                    batch_ids = []
                    batch_texts = []

            segsdone += len(sentslice)
            pct = int(100 * segsdone / segcount)
            progress = f"[{docnum}"
            if doccount > 0:
                progress += f"/{doccount}"
            progress += f"] {doc.filename} {pct}%"
            print(f"\r{progress:<79}", end="", file=sys.stderr, flush=True)

        print(file=sys.stderr)

    # Flush remaining segments from the last partial batch
    flush_batch(collection, batch_ids, batch_texts, embedmodel)

    print(f"\nDone: {docnum} documents processed, {skipped} skipped.", file=sys.stderr)


########## main

def Usage(s=""):
    print(f"{s}", file=sys.stderr)
    print(f"Usage: {os.path.basename(sys.argv[0])} [-c confdir]", file=sys.stderr)
    sys.exit(1)
    
confdir=""
try:
    options, args = getopt.getopt(sys.argv[1:], "c:")
except Exception as ex:
    Usage(str(ex))
for opt,val in options:
    if opt == "-c":
        confdir = val
    else:
        Usage(f"bad option {opt}")


rcldb, collection, embedmodel, embedsegsize = common_init(confdir)

update_embeddings(rcldb, collection, embedmodel, embedsegsize)
