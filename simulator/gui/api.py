"""What the GUI's JSON endpoints answer with.

**Nothing here scores anything, and nothing here can.**  This module used to hold the
whole of `POST /api/evaluate` — request validation, a block loop, twenty calls into the
harness per click.  All of it moved to `bench/catalog.py`, which runs offline (8.11), and
what is left is the one question a serving process still answers about itself.

The catalog document is read by the server at startup and served as it was built; there is
no shaping to do here because 8.11.1 put the document in the shape the page reads.
"""

from __future__ import annotations

import os

from . import SERVICE


def health(dataset_id=None, started: str | None = None, identified: bool = True) -> dict:
    """This process's identity, so a launcher can recognise it (12.2.9).

    A launch has two questions to answer before it binds a socket: is anything listening,
    and is that thing this server.  Both are answered over the interface the process is
    already serving, so recognising an instance needs nothing on disk to be found, agreed
    on, or cleaned up afterwards (12.2.9.1).

    The pid is what makes a shutdown addressable, and the dataset id and start time are
    here so a reader who meets a running instance is told *which* demonstration it is
    before being asked whether to replace it.  The id is the corpus the **catalogue** was
    built against (8.11.1) — this process never loaded one (12.2.3) — which is the honest
    answer to "which demonstration is this" now that the numbers are pre-computed.

    `identified` is false for the one caller that reaches this endpoint without coming
    through the front door: a platform's readiness probe, admitted by 12.2.15's single
    exemption.  It is asking whether this is up, and everything above is answering a
    question it did not ask, so it is told the signature and nothing else.  The signature
    stays because it is what distinguishes this service from another one answering the
    same path, and it identifies the *software*, never the instance.
    """
    if not identified:
        return {"service": SERVICE}
    return {
        "service": SERVICE,
        "pid": os.getpid(),
        "dataset_id": dataset_id,
        "started": started,
    }
