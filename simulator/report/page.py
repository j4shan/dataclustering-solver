"""The report page.

Text is limited to a page title, the dataset id and run timestamp, and one title per
chart.  No prose — the charts carry the result.
"""

from __future__ import annotations

from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{
    --surface: #fcfcfb; --ink: #0b0b0b; --ink-muted: #52514e; --rule: #e4e3df;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --surface: #1a1a19; --ink: #ffffff; --ink-muted: #c3c2b7; --rule: #383835; }}
  }}
  body {{
    margin: 0; padding: 2.5rem 1.5rem 4rem; background: var(--surface); color: var(--ink);
    font: 15px/1.6 ui-sans-serif, -apple-system, "Segoe UI", Roboto, sans-serif;
  }}
  main {{ max-width: 62rem; margin: 0 auto; }}
  h1 {{ font-size: 1.35rem; font-weight: 600; margin: 0 0 .35rem; }}
  h2 {{ font-size: 1rem; font-weight: 600; margin: 2.75rem 0 .75rem; }}
  .meta {{ color: var(--ink-muted); font-size: .82rem; font-family: ui-monospace, monospace; }}
  figure {{ margin: 0; overflow-x: auto; }}
  svg, img {{ max-width: 100%; height: auto; }}
  table {{ border-collapse: collapse; font-size: .8rem; width: 100%; }}
  th, td {{ text-align: right; padding: .3rem .6rem; border-bottom: 1px solid var(--rule); }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ color: var(--ink-muted); font-weight: 600; }}
  details {{ margin-top: 2.5rem; }}
  summary {{ cursor: pointer; color: var(--ink-muted); font-size: .85rem; }}
</style>
</head>
<body>
<main>
  <h1>{title}</h1>
  <p class="meta">dataset {dataset_id} &middot; {event_count} events &middot; {query_count} queries
     &middot; rendered {timestamp}</p>
  {sections}
  <details>
    <summary>Metric table</summary>
    {table}
  </details>
</main>
</body>
</html>
"""

SECTION = """  <h2>{heading}</h2>
  <figure>
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="{dark}">
      <img alt="{heading}" src="{light}">
    </picture>
  </figure>
"""

CHART_TITLES = {
    "scatter": "Byte skipping against management cost",
    "sweep": "Byte skipping against container capacity",
    "period": "Byte skipping against query position",
}

#: Skipping ratios lead — they are the headline KPIs. Waste ratio follows as the
#: formulation's objective, and read amplification as the unit systems usually report.
TABLE_COLUMNS = (
    "Strategy_Name",
    "Set_Name",
    "target_container_rows",
    "container_count",
    "record_skip_ratio",
    "byte_skip_ratio",
    "container_skip_ratio",
    "waste_ratio",
    "read_amplification",
    "management_cost",
)


def _table(rows) -> str:
    head = "".join(f"<th>{c}</th>" for c in TABLE_COLUMNS)
    body = []
    for row in rows:
        cells = []
        for column in TABLE_COLUMNS:
            value = row.get(column)
            if isinstance(value, float):
                value = f"{value:.4g}"
            cells.append(f"<td>{value}</td>")
        body.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def render(rows, charts: dict[str, dict[str, Path]], dataset, out: str | Path, timestamp: str):
    out = Path(out)
    sections = "".join(
        SECTION.format(
            heading=CHART_TITLES[key],
            light=charts["light"][key].name,
            dark=charts["dark"][key].name,
        )
        for key in ("scatter", "sweep", "period")
    )
    out.write_text(
        TEMPLATE.format(
            title="Data Layout Simulator",
            dataset_id=dataset.dataset_id,
            event_count=f"{dataset.event_count:,}",
            query_count=f"{dataset.query_count:,}",
            timestamp=timestamp,
            sections=sections,
            table=_table(rows),
        )
    )
    return out
