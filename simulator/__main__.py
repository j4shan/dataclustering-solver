"""Command line entry point.

    python -m simulator generate                        build the synthetic dataset
    python -m simulator generate --provider external --source DIR
                                                        adopt an external CSV export
    python -m simulator gui                             serve the presentation page (foreground)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import gui as gui_package
from . import logs

log = logs.get(__name__)

# -- corpus generation, imported late -------------------------------------------------
#
# 10.3.1 splits the dependency set in two: building a corpus needs numpy and pyarrow, and
# serving the page needs an ASGI stack and nothing more.  `gui` is in the second set, so
# importing numpy at module scope would make `simulator gui` fail on a page-only install
# for want of a library it never calls — and 10.3.9 asks that such a command fail saying
# which group supplies what is missing, not with an ImportError naming a package the
# reader never asked for.
#
# So every such import sits inside the function that needs it — Python's ordinary idiom
# for a deferred import — and `main` turns the one failure they share into that sentence.

#: The command that needs it, and the extra that supplies it (10.3.9).
DATA_GROUP = "data"
DATA_COMMANDS = frozenset({"generate"})

SUBCOMMANDS = ("generate", "gui")

NO_SUBCOMMAND_HELP = "name a subcommand:\n    generate | gui"

GENERATED_ROOT = Path("data/generated")


def _build(provider_name: str, config, path: Path, **kwargs) -> None:
    from . import providers

    started = time.perf_counter()
    providers.get(provider_name)(config, path, **kwargs)
    elapsed = time.perf_counter() - started
    log.info("built provider=%s path=%s elapsed=%.1fs", provider_name, path, elapsed)
    print(f"{provider_name} dataset at {path} in {elapsed:.1f}s")


def _describe(dataset) -> None:
    import numpy as np

    from .core import contract
    from .core import packed_support

    event_support_size = packed_support.support_size(dataset.event_support)
    training = dataset.training_query_indices()
    validation = np.flatnonzero(dataset.set_name == contract.VALIDATION)

    visible = packed_support.support_size(
        packed_support.restrict_to_queries(
            dataset.event_support, training, dataset.query_count
        )
    )
    wanted_later = (
        packed_support.support_size(
            packed_support.restrict_to_queries(
                dataset.event_support, validation, dataset.query_count
            )
        )
        > 0
    )
    never_selected = event_support_size == 0
    cold = wanted_later & (visible == 0)

    print(f"  dataset_id           {dataset.dataset_id}")
    print(f"  provider             {dataset.manifest.get('provider', 'unknown')}")
    print(f"  events / queries     {dataset.event_count:,} / {dataset.query_count:,}")
    print(f"  selection log rows   {dataset.manifest['selection_log_rows']:,}")
    print(
        f"  never selected       {never_selected.sum():,} events"
        f"  ({never_selected.mean() * 100:.1f}%)"
    )
    print(
        f"  cold for a strategy  {cold.sum():,} events"
        f"  ({cold.sum() / max(wanted_later.sum(), 1) * 100:.1f}% of held-out demand)"
    )
    print(
        f"  corpus               {dataset.compressed_bytes.sum() / 1e9:.2f} GB compressed"
        f" / {dataset.decompressed_bytes.sum() / 1e9:.2f} GB decompressed"
    )
    print(
        f"  event size mean/p99  {dataset.compressed_bytes.mean() / 1e3:.1f} KB"
        f" / {np.percentile(dataset.compressed_bytes, 99) / 1e3:.1f} KB compressed"
    )
    print(f"  query time span      {dataset.query_time.min()} .. {dataset.query_time.max()}")


def cmd_generate(args):
    from . import providers
    from .core import dataset as dataset_module
    from .providers.synthetic import DatasetConfig

    # Checked here rather than by `choices=` on the parser: reading the registry to build
    # the parser would import the providers — and with them numpy — on every invocation,
    # including `gui`, which 10.3.1 keeps clear of the harness.
    if args.provider not in providers.available():
        raise SystemExit(
            f"unknown provider {args.provider!r}; "
            f"choose from {', '.join(sorted(providers.available()))}"
        )
    if args.provider == "external":
        path = GENERATED_ROOT / (args.name or "external")
        _build("external", None, path, source=args.source)
    else:
        config = DatasetConfig()
        _build("synthetic", config, GENERATED_ROOT / config.name)
        path = GENERATED_ROOT / config.name
    _describe(dataset_module.load(path))


def cmd_gui(args):
    # Imported here rather than at module scope so that `generate` never pays for the
    # server, and so this module keeps importing on a checkout where the GUI package is
    # not yet built out.
    from .gui.server import serve

    return serve(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser and sys.stdin.isatty(),
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="simulator")
    subcommands = parser.add_subparsers(dest="command", required=False)

    generate = subcommands.add_parser("generate")
    generate.add_argument("--provider", default="synthetic", help="dataset provider")
    generate.add_argument("--source", help="CSV export directory, for --provider external")
    generate.add_argument("--name", help="directory name under data/generated")
    generate.set_defaults(func=cmd_generate)

    gui = subcommands.add_parser("gui", help="serve the presentation page on loopback")
    gui.add_argument("--host", default=None, help=f"bind address (default {gui_package.DEFAULT_HOST})")
    gui.add_argument("--port", type=int, default=None, help=f"port (default {gui_package.DEFAULT_PORT})")
    gui.add_argument("--no-browser", action="store_true", help="do not open a browser")
    gui.set_defaults(func=cmd_gui)

    args = parser.parse_args(argv)

    if not args.command:
        # Nothing to default to: `generate` builds a corpus and `gui` serves the page,
        # and guessing which was meant is not this command's to do.
        print(NO_SUBCOMMAND_HELP)
        return 1

    # Once, before any work: everything below logs through the `simulator` logger, and
    # the run file is named for the moment the command started rather than the moment it
    # first had something to say (10.3.7).
    run_file = logs.configure(args.command)
    print(f"log  {run_file}")

    try:
        return args.func(args) or 0
    except ImportError as missing:
        # Scoped to the command that needs the extra, so a genuine import bug anywhere
        # else still raises as itself rather than being reported as a missing install.
        if args.command not in DATA_COMMANDS:
            raise
        raise SystemExit(
            f"`simulator {args.command}` needs the data extra, and {missing.name} is not"
            f" installed.\n    pip install -e '.[{DATA_GROUP}]'"
        ) from None


if __name__ == "__main__":
    sys.exit(main())
