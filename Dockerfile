# The deployment artifact (10.3.12).  One image serves a laptop and a public instance;
# everything that differs between them arrives in the environment, never in a second
# code path or a second image.
#
# **One stage, and no corpus** (10.3.12.1).  This used to be two: the first generated a
# 600 000-event corpus so the second could hold it in memory and score layouts inside a
# request.  Section B now presents a catalogue computed ahead of serving (8.11), so the
# image needs neither the corpus nor the libraries that produce one — 124 MB of data and
# 174 MB of numeric wheels, both gone, for a serving process that answers every request
# it can receive out of one 160 kB document.
#
# **The catalog document is a build input.**  It is produced by the recompute job, which
# runs when the corpus version or the metric schema changes rather than on every deploy:
#
#     python -m simulator catalog --dataset <the versioned corpus> \
#         --out data/catalog/strategy-catalog.json
#
# The corpus that command reads is a versioned external asset, identified by the dataset
# id its configuration hashes to (4.10), and it never enters this image.  Put the
# resulting document in the build context before building; `COPY` fails the build if it
# is missing, which is the intended behaviour — an instance that served an empty Section
# B would be worse than one that never started.

FROM python:3.12-slim

# Not root, because nothing this process does needs to be.
RUN useradd --create-home --uid 10001 app
WORKDIR /app
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# The dependency set before the source, so a source edit does not reinstall the world.
# The default install is the **exhibit** half of 10.3.1 — FastAPI and uvicorn — and the
# `harness` extra is deliberately not named here.
COPY pyproject.toml uv.lock README.md ./
COPY simulator ./simulator
COPY resources ./resources
RUN pip install --no-cache-dir .

# What the page is drawn from.  160 kB, where the corpus behind it is 124 MB.
COPY data/catalog/strategy-catalog.json /app/data/catalog/strategy-catalog.json

# The one writable path this process needs.  10.3.7 makes a run file part of every run,
# and `/app` belongs to root, so the directory is created and handed over here rather
# than left for a non-root process to fail on at its first log line.
RUN mkdir -p /app/data/logs && chown app:app /app/data/logs
ENV SIMULATOR_LOG_DIR=/app/data/logs

USER app

# Defaults for a container.  The platform overrides `PORT`; the front door supplies the
# rest, and `GUI_FRONT_DOOR_SECRET` must be set for 12.2.15 to be doing anything.
ENV GUI_HOST=0.0.0.0 \
    PORT=8765 \
    GUI_MOUNT_PREFIX=/dataclustering

EXPOSE 8765

# What the platform asks before routing to this instance (12.2.9.1).  The catalog is read
# before the socket binds, so a reply at all is the readiness answer.  The start period is
# short now that starting means parsing one document rather than loading a corpus.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request;urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/health',timeout=4)"

# One worker: the catalog is held in memory per process (10.3.12), so a second would
# duplicate it to serve the same immutable document.
#
# `exec` is load-bearing, not tidiness.  A shell is needed to expand the two variables,
# but without `exec` that shell stays as pid 1 and the server runs as its child — and a
# pid 1 shell does not forward signals.  Every platform stops a container by sending
# `SIGTERM` to pid 1, so the server would never see it, never close its listener, and be
# killed at the end of the grace period on every single deploy, contradicting 12.2.10.
CMD ["sh", "-c", "exec python -m simulator gui --host \"$GUI_HOST\" --port \"$PORT\" --no-browser"]
