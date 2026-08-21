"""Charts, rendered to SVG in a light and a dark variant.

Colour carries strategy identity, so hues are assigned in fixed order and never
cycled — a strategy keeps its hue however many series a chart happens to show.  The
palettes below are the reference categorical slots 1 and 2, validated against both
surfaces (lightness band, chroma floor, CVD separation, normal-vision floor, contrast).

Every chart reads the metric table only, so all three regenerate without rerunning any
evaluation.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Fixed hue order.  Slot n always means the nth strategy encountered, never rank.
SERIES_LIGHT = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
SERIES_DARK = ("#3987e5", "#d95926", "#199e70", "#c98500")


@dataclass(frozen=True)
class Theme:
    name: str
    surface: str
    ink: str
    ink_secondary: str
    grid: str
    series: tuple[str, ...]


LIGHT = Theme("light", "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", SERIES_LIGHT)
DARK = Theme("dark", "#1a1a19", "#ffffff", "#c3c2b7", "#383835", SERIES_DARK)


def _figure(theme: Theme, size=(7.6, 4.4)):
    fig, ax = plt.subplots(figsize=size)
    fig.patch.set_facecolor(theme.surface)
    ax.set_facecolor(theme.surface)
    # Recessive axes and grid: the data should be the only assertive thing here.
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(theme.grid)
    ax.tick_params(colors=theme.ink_secondary, labelsize=9, length=3)
    ax.grid(True, color=theme.grid, linewidth=0.8, alpha=0.9)
    ax.set_axisbelow(True)
    return fig, ax


def _finish(fig, ax, theme: Theme, title: str, xlabel: str, ylabel: str, path: Path):
    ax.set_title(title, color=theme.ink, fontsize=11.5, loc="left", pad=12)
    ax.set_xlabel(xlabel, color=theme.ink_secondary, fontsize=9.5)
    ax.set_ylabel(ylabel, color=theme.ink_secondary, fontsize=9.5)
    legend = ax.get_legend()
    if legend:
        legend.get_frame().set_facecolor(theme.surface)
        legend.get_frame().set_edgecolor(theme.grid)
        for text in legend.get_texts():
            # Text wears ink, never the series colour; the swatch beside it carries identity.
            text.set_color(theme.ink_secondary)
            text.set_fontsize(9)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="svg", facecolor=theme.surface)
    plt.close(fig)


def _end_labels(fig, ax, entries, theme: Theme, min_gap_px: float = 13.0) -> None:
    """Direct-label each series at its last point, pushing labels apart if they collide.

    Series that converge — which is exactly what happens once containers grow large
    enough that every query opens all of them — would otherwise overprint their labels.
    """
    if not entries:
        return
    fig.canvas.draw()
    heights = [ax.transData.transform((x, y))[1] for x, y, _ in entries]

    placed: dict[int, float] = {}
    previous = None
    for index in sorted(range(len(entries)), key=lambda i: -heights[i]):
        target = heights[index]
        if previous is not None and previous - target < min_gap_px:
            target = previous - min_gap_px
        placed[index] = target
        previous = target

    points_per_pixel = 72.0 / fig.dpi
    for index, (x, y, label) in enumerate(entries):
        ax.annotate(
            label,
            (x, y),
            textcoords="offset points",
            xytext=(7, (placed[index] - heights[index]) * points_per_pixel),
            color=theme.ink_secondary,
            fontsize=8.5,
            va="center",
            annotation_clip=False,
        )


def _strategy_colors(strategies, theme: Theme) -> dict[str, str]:
    return {name: theme.series[i % len(theme.series)] for i, name in enumerate(strategies)}


def _strategies(rows) -> list[str]:
    seen = []
    for row in rows:
        if row["Strategy_Name"] not in seen:
            seen.append(row["Strategy_Name"])
    return seen


def scatter_kpi_vs_cost(rows, out: Path, theme: Theme = LIGHT) -> Path:
    """Where the granularity trade-off becomes legible."""
    fig, ax = _figure(theme)
    colors = _strategy_colors(_strategies(rows), theme)

    for name, color in colors.items():
        for set_name, marker, fill in (
            ("training", "o", "none"),
            ("validation", "o", color),
        ):
            pts = [
                r
                for r in rows
                if r["Strategy_Name"] == name and r["Set_Name"] == set_name
            ]
            if not pts:
                continue
            ax.scatter(
                [r["management_cost"] for r in pts],
                [r["byte_skip_ratio"] for r in pts],
                s=58,
                marker=marker,
                facecolors=fill,
                edgecolors=color,
                linewidths=1.8,
                label=f"{name} · {set_name}",
                zorder=3,
            )

    ax.set_xscale("log")
    ax.set_ylim(0.0, 1.0)
    ax.legend(loc="best", frameon=True, fontsize=9)
    _finish(
        fig,
        ax,
        theme,
        "Byte skipping against management cost — higher is better",
        "management cost (abstract units, log)",
        "byte skipping ratio — share of corpus bytes not read",
        out,
    )
    return out


def line_kpi_vs_container_size(rows, out: Path, theme: Theme = LIGHT) -> Path:
    """The sweep: what buying finer containers actually buys.

    The x axis is the swept capacity in records (7.2.3.1).  Bytes remain the *measure* on
    the y axis — the share of corpus bytes a query avoided reading.
    """
    fig, ax = _figure(theme)
    colors = _strategy_colors(_strategies(rows), theme)
    ends: list[tuple[float, float, str]] = []

    for name, color in colors.items():
        pts = sorted(
            (
                r
                for r in rows
                if r["Strategy_Name"] == name and r["Set_Name"] == "validation"
            ),
            key=lambda r: r["target_container_rows"],
        )
        if not pts:
            continue
        x = [r["target_container_rows"] for r in pts]
        y = [r["byte_skip_ratio"] for r in pts]
        ax.plot(x, y, color=color, linewidth=2.0, marker="o", markersize=5, label=name, zorder=3)
        ends.append((x[-1], y[-1], name))

    ax.set_xscale("log")
    ax.set_ylim(0.0, 1.0)
    ax.margins(x=0.30)
    ax.legend(loc="best", frameon=True, fontsize=9)
    # Direct labels as well as the legend: identity is never colour alone.
    _end_labels(fig, ax, ends, theme)
    _finish(
        fig,
        ax,
        theme,
        "Byte skipping against container capacity — validation queries",
        "container capacity, records (log)",
        "byte skipping ratio — share of corpus bytes not read",
        out,
    )
    return out


def line_kpi_vs_period(series: dict[str, dict[str, float]], out: Path, theme: Theme = LIGHT):
    """Held-out byte skipping ratio by the calendar month a query ran in.

    No slope is fitted and no direction is implied.  A layout's skipping on a query
    depends on how similar that query is to the ones it was built from, not on how far
    away it sits in time, so this curve may fall, flatten, or rise again as demand
    returns to regions the layout already suits.
    """
    fig, ax = _figure(theme)
    colors = _strategy_colors(list(series), theme)

    periods = sorted({p for points in series.values() for p in points})
    for name, points in series.items():
        y = [points.get(p) for p in periods]
        ax.plot(
            periods,
            y,
            color=colors[name],
            linewidth=2.0,
            marker="o",
            markersize=5,
            label=name,
            zorder=3,
        )

    ax.set_ylim(0.0, 1.0)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="best", frameon=True, fontsize=9)
    _finish(
        fig,
        ax,
        theme,
        "Byte skipping against query position — validation queries by month issued",
        "month the query was issued",
        "byte skipping ratio — share of corpus bytes not read",
        out,
    )
    return out


def render_all(rows, skip_ratio_by_period_per_strategy, out_dir: str | Path) -> dict[str, dict[str, Path]]:
    out_dir = Path(out_dir)
    produced: dict[str, dict[str, Path]] = {}
    for theme in (LIGHT, DARK):
        suffix = theme.name
        produced[suffix] = {
            "scatter": scatter_kpi_vs_cost(rows, out_dir / f"scatter.{suffix}.svg", theme),
            "sweep": line_kpi_vs_container_size(rows, out_dir / f"sweep.{suffix}.svg", theme),
            "period": line_kpi_vs_period(
                skip_ratio_by_period_per_strategy, out_dir / f"period.{suffix}.svg", theme
            ),
        }
    return produced
