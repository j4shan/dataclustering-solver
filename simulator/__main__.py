"""Command line entry point.

    python -m simulator                                 interactive control plane (8.9.1)
    python -m simulator generate                        build the synthetic dataset
    python -m simulator generate --provider external --source DIR
                                                        adopt an external CSV export
    python -m simulator catalog                         score the catalogue the page presents
    python -m simulator run                             sweep, then render the report
    python -m simulator gui                             serve the demonstration GUI (foreground)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import gui as gui_package
from . import logs

log = logs.get(__name__)

# -- the harness, imported late ------------------------------------------------------
#
# 10.3.1 splits the dependency set in two: the **harness** (numpy, pyarrow, matplotlib)
# generates a corpus, scores a layout and renders a report, and the **exhibit** (an ASGI
# stack, nothing more) serves the page.  `gui` is in the second set, so importing numpy at
# module scope would make `simulator gui` fail on an exhibit install for want of a library
# it never calls — and 10.3.9 asks that such a command fail saying which group supplies
# what is missing, not with an ImportError naming a package the reader never asked for.
#
# So every harness import sits inside the function that needs it — Python's ordinary
# idiom for a deferred import — and `main` turns the one failure they share into that
# sentence.  `cmd_gui` already imported its own dependencies this way; this extends the
# same pattern to the other direction.

#: The commands that need it, and the extra that supplies it (10.3.9).
HARNESS_GROUP = "harness"
HARNESS_COMMANDS = frozenset({"generate", "run", "catalog"})

SUBCOMMANDS = ("generate", "catalog", "run", "gui")

NO_TERMINAL_HELP = (
    "no terminal to open the control plane — use a subcommand:\n"
    "    generate | catalog | run | gui"
)

GENERATED_ROOT = Path("data/generated")
REPORT_ROOT = Path("data/report")

#: Where the catalog document is written and where `gui` looks for one (8.11, 12.2.3).
#: Under `data/` — which `.gitignore` anchors at the repository root — and deliberately
#: *not* beside the committed scenario file in `resources/data/`: a generated artifact and
#: a versioned one sharing a directory is how an ignore rule written for the first comes
#: to swallow the second (10.3.10).
CATALOG_ROOT = Path("data/catalog")
CATALOG_FILE = CATALOG_ROOT / "strategy-catalog.json"


def _build(provider_name: str, config, path: Path, **kwargs) -> None:
    from . import providers

    started = time.perf_counter()
    providers.get(provider_name)(config, path, **kwargs)
    elapsed = time.perf_counter() - started
    log.info("built provider=%s path=%s elapsed=%.1fs", provider_name, path, elapsed)
    print(f"{provider_name} dataset at {path} in {elapsed:.1f}s")


def _load_or_build(config, rebuild: bool = False):
    from .core import contract
    from .core import dataset as dataset_module

    path = GENERATED_ROOT / config.name
    if rebuild or not (path / contract.MANIFEST_FILE).exists():
        print("building the auto part sales dataset (first run only)…")
        _build("synthetic", config, path)
    return dataset_module.load(path)


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


def cmd_run(args):
    from .bench import metrics
    from .bench.runner import (
        add_baseline_lift,
        skip_ratio_by_period_per_strategy,
        sweep,
    )
    from .config import SweepConfig
    from .core import dataset as dataset_module
    from .providers.synthetic import DatasetConfig
    from .report import charts, page

    config = DatasetConfig()
    if args.dataset:
        dataset = dataset_module.load(args.dataset)
    else:
        dataset = _load_or_build(config, rebuild=args.rebuild)
    _describe(dataset)

    sweep_config = SweepConfig()

    print("\nsweep:")
    started = time.perf_counter()
    rows = add_baseline_lift(sweep(dataset, sweep_config))
    print(f"sweep finished in {time.perf_counter() - started:.1f}s")

    default_rows = sweep_config.default_rows
    print(
        f"\nbyte skipping ratio by month issued"
        f" (validation, {default_rows}-record containers):"
    )
    by_period = skip_ratio_by_period_per_strategy(
        dataset, sweep_config, sweep_config.default_rows
    )
    for strategy_name, points in by_period.items():
        rendered = "  ".join(f"{p}:{v:.2f}" for p, v in sorted(points.items()))
        print(f"  {strategy_name:<18} {rendered}")

    out_dir = REPORT_ROOT / dataset.dataset_id
    rendered_charts = charts.render_all(rows, by_period, out_dir)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    html = page.render(rows, rendered_charts, dataset, out_dir / "index.html", timestamp)
    print(f"\nreport  {html}")
    print(f"metrics {metrics.DEFAULT_DIR}")


def cmd_catalog(args):
    """Score the catalogue Section B presents, and write it as one document (8.11).

    This is the command that replaced the browser's Evaluate button.  It runs offline
    against a corpus — the locally bootstrapped one, or a versioned copy fetched from
    wherever the deployment keeps it — and its output is what a serving instance reads.
    """
    import json

    from .bench import catalog as catalog_module
    from .core import dataset as dataset_module
    from .providers.synthetic import DatasetConfig

    dataset = (
        dataset_module.load(args.dataset)
        if args.dataset
        else _load_or_build(DatasetConfig())
    )
    _describe(dataset)

    print(f"\nscoring {len(catalog_module.DEFINITION)} strategies…")
    started = time.perf_counter()
    document = catalog_module.build(dataset)
    elapsed = time.perf_counter() - started

    out = Path(args.out) if args.out else CATALOG_FILE
    out.parent.mkdir(parents=True, exist_ok=True)
    # Indented rather than compact: 10.3.4 keeps data formats inspectable and diffable,
    # and the size this costs is kilobytes on a document already measured in hundreds.
    out.write_text(json.dumps(document, indent=1, default=str), encoding="utf-8")

    for entry in document["strategies"]:
        chain = " · ".join(
            f"{stage['expression']} → {stage['splits']:,}" for stage in entry["stages"]
        )
        print(f"  {entry['id']:<20} {chain or 'no stage'}")
    print(
        f"\ncatalog {out}  "
        f"({len(document['rows'])} rows, {out.stat().st_size / 1000:.0f} kB, {elapsed:.1f}s)"
    )


def cmd_menu(_args):
    """Numbered control plane.  Only reached when stdin is a terminal (8.9.1)."""
    from . import menu

    return menu.run()


def cmd_gui(args):
    # Imported here rather than at module scope so that `generate` and `run` never pay
    # for the server, and so this module keeps importing on a checkout where the GUI
    # package is not yet built out.
    import json

    from .gui import Deployment, launcher
    from .gui.server import serve

    # Where this process is serving *as* (10.3.12): loopback on a laptop, and whatever
    # the platform hands it in a container.  A flag still wins, because a reader who
    # typed one meant it.
    deployment = Deployment.from_environment()
    host = deployment.host if args.host is None else args.host
    port = deployment.port if args.port is None else args.port

    # Before the dataset, not after (12.2.8).  Loading it first would spend a
    # 600 000-event build on `--stop`, or on an answer of "leave it running", before
    # discovering there was nothing to launch.
    found = launcher.probe(host, port)
    interactive = sys.stdin.isatty()
    requested = launcher.SHUTDOWN if args.stop else None
    requested = launcher.RESTART if args.restart else requested

    # Only a reader at a terminal is asked, and only when a flag has not already said
    # what to do (12.2.11).
    asked = (
        launcher.ask(found)
        if found.state is launcher.State.OURS and requested is None and interactive
        else None
    )
    action = launcher.decide(found, requested, asked)

    if action is launcher.Action.PORT_BUSY:
        print(f"port {port} on {host} is held by another process")
        print("stop that process, or serve somewhere else with --port")
        return 1
    if action is launcher.Action.UNDECIDED:
        print(launcher.describe(found))
        print("no terminal to ask at — re-run with --restart or --stop")
        return 1
    if action is launcher.Action.NOTHING_TO_STOP:
        print(f"nothing is serving on {found.url}")
        return 0
    if action is launcher.Action.KEEP:
        print(f"left running  {found.url}")
        return 0
    if action in (launcher.Action.STOP, launcher.Action.STOP_THEN_LAUNCH):
        print(f"stopping pid {found.pid}…")
        if not launcher.stop(found):
            print(f"pid {found.pid} did not stop — `kill -9 {found.pid}` to force it")
            return 1
        print("stopped")
        if action is launcher.Action.STOP:
            return 0

    # Read before the socket is bound, once, for the process's life (12.2.3).  A
    # document, not a corpus: this command imports no part of the harness and this
    # process holds no dataset (10.3.1).
    catalog_path = Path(args.catalog) if args.catalog else CATALOG_FILE
    if not catalog_path.exists():
        # Named rather than served empty: a missing catalogue is a bootstrap step the
        # reader has not run yet, and 10.3.9 asks that it say which one.
        print(f"no catalog at {catalog_path}")
        print("build one first:")
        print("    python -m simulator generate     # bootstrap a corpus")
        print("    python -m simulator catalog      # score the catalogue")
        return 1
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as unreadable:
        print(f"could not read the catalog at {catalog_path}: {unreadable}")
        return 1

    return serve(
        host=host,
        port=port,
        catalog=catalog,
        open_browser=not args.no_browser and interactive,
        deployment=deployment,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="simulator")
    subcommands = parser.add_subparsers(dest="command", required=False)

    generate = subcommands.add_parser("generate")
    generate.add_argument("--provider", default="synthetic", help="dataset provider")
    generate.add_argument("--source", help="CSV export directory, for --provider external")
    generate.add_argument("--name", help="directory name under data/generated")
    generate.set_defaults(func=cmd_generate)

    run = subcommands.add_parser("run")
    run.add_argument("--dataset", help="score an existing dataset directory")
    run.add_argument("--rebuild", action="store_true")
    run.set_defaults(func=cmd_run)

    catalog = subcommands.add_parser(
        "catalog", help="score the catalogue the GUI presents (8.11)"
    )
    catalog.add_argument("--dataset", help="build against an existing dataset directory")
    catalog.add_argument("--out", help=f"where to write it (default {CATALOG_FILE})")
    catalog.set_defaults(func=cmd_catalog)

    gui = subcommands.add_parser("gui", help="serve the demonstration GUI on loopback")
    # Defaulted from the environment rather than here, so one image serves a laptop and
    # a container without a second code path (10.3.12).
    gui.add_argument("--host", default=None, help=f"bind address (default {gui_package.DEFAULT_HOST})")
    gui.add_argument("--port", type=int, default=None, help=f"port (default {gui_package.DEFAULT_PORT})")
    gui.add_argument("--catalog", help=f"catalog document to serve (default {CATALOG_FILE})")
    gui.add_argument("--no-browser", action="store_true", help="do not open a browser")
    # Mutually exclusive because they are answers to the same question, and asking for
    # both says nothing about which is meant (12.2.11).
    lifecycle = gui.add_mutually_exclusive_group()
    lifecycle.add_argument("--stop", action="store_true", help="shut a running instance down")
    lifecycle.add_argument("--restart", action="store_true", help="stop it, then launch")
    gui.set_defaults(func=cmd_gui)

    args = parser.parse_args(argv)

    if not args.command:
        if not sys.stdin.isatty():
            print(NO_TERMINAL_HELP)
            return 1
        args.command = "menu"
        args.func = cmd_menu

    # Once, before any work: everything below logs through the `simulator` logger, and
    # the run file is named for the moment the command started rather than the moment it
    # first had something to say (10.3.7).
    run_file = logs.configure(args.command)
    print(f"log  {run_file}")

    try:
        return args.func(args) or 0
    except ImportError as missing:
        # Scoped to the commands that need the harness, so a genuine import bug anywhere
        # else still raises as itself rather than being reported as a missing install.
        if args.command not in HARNESS_COMMANDS:
            raise
        raise SystemExit(
            f"`simulator {args.command}` needs the harness, and {missing.name} is not"
            f" installed.\n    pip install -e '.[{HARNESS_GROUP}]'"
        ) from None


if __name__ == "__main__":
    sys.exit(main())
