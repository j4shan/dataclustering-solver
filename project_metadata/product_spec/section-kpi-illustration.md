# Business Signal in Cold Data illustration

Product requirements for the Business Signal in Cold Data section of the
demonstration GUI: one scrolling pane that states how a usage-shaped
layout quarantines idle clusters, then shows that reading on three
domain maps.

**Authority.** This document is the product spec for Business Signal in
Cold Data. [`simulator-spec.md`](simulator-spec.md) governs the
application shell, theme, and layout.
[`problem-statement.md`](../../site/docs/problem-statement.md)
remains the authority on the formal model. Where this document and the
product spec disagree on shell, theme, or layout, the product spec wins.
Where they disagree on this section's content, this document wins.

**No recommendation.** The pane may show that unused clusters on a usage
map are the same populations a skip layout would quarantine. It does not
select, rank, or recommend an assignment strategy, a search method, or a
fitness. It does not claim a business result.

---

## 1. Role and reading order

Business Signal in Cold Data is the fifth section. It sits after Go Live
on Databricks Lakehouse. The section heading is the navigation label.

One pane, independently scrollable on a wide viewport. No left/right
split. Below the split breakpoint the pane grows with its content and
the page scrolls once.

Sequence:

1. the opening paragraph;
2. the advertising paragraph, then figure `signal.advertising`;
3. the ecommerce paragraph, then figure `signal.ecommerce`;
4. the social paragraph, then figure `signal.social`.

The four paragraphs and the three captions are fixed below. The fragment
copies them. It does not rewrite them.

The pane does not use the word *teach*. The pane does not use the word
*production*. Conclusions stay in the last sentence of each paragraph.
There is no labeled takeaway.

---

## 2. Reader-facing prose

### 2.1 Opening

A data layout shaped by query usage often follows the same concentrations a business already records as KPIs. Split search isolates the cold and hot segments of a corpus; a multiple-choice knapsack then spends a limited container budget where the skipping benefit is largest. The search that builds a skip layout also quarantines subclusters that queries almost never touch. Those idle clusters name the campaigns, products, or posts that fail the KPI the queries were written to serve.

### 2.2 Digital advertising

A conversion query selects the events that ended in a sale. Campaigns that never convert stay in the corpus as real bytes with zero demand. Split search puts those events in cold leaves, and the knapsack spends almost no extra containers on them. On the map, tile area is ad spend and brightness is conversion rate. The large dim tiles are spend on campaigns that do not convert.

### 2.3 Ecommerce warehouse

A pick-and-pack query selects the SKUs that sell. Products that do not move are never selected, so they land in a cold leaf. Tile area is on-hand inventory and brightness is sell-through. The pale tiles are stock those queries have already treated as unused.

### 2.4 Social media

Queries that measure engagement select the posts that received it. Posts that received none are missing from the selection log. Tile area is impressions and brightness is engagement rate. The dim cluster is content those queries already skip.

---

## 3. Figures

The pane contains exactly three figures, in that reading order. Each
raster is deferred. The pane does not reference a missing file. Each
figure is a title, an empty stage, and the caption. The prompt is the
authority on what the accepted raster will show.

| id | Visible title | Prompt |
| --- | --- | --- |
| `signal.advertising` | Ad Spend and Conversion | [`section_kpi_advertising_prompt.txt`](../../resources/img_prompt/section_kpi_advertising_prompt.txt) |
| `signal.ecommerce` | On-hand Inventory and Sell-through | [`section_kpi_ecommerce_prompt.txt`](../../resources/img_prompt/section_kpi_ecommerce_prompt.txt) |
| `signal.social` | Impressions and Engagement | [`section_kpi_social_prompt.txt`](../../resources/img_prompt/section_kpi_social_prompt.txt) |

Captions, in figure order:

- Tile area is ad spend and brightness is conversion rate. The large dim group is spend that did not convert.
- Tile area is on-hand inventory and brightness is sell-through. The pale group is stock that does not sell.
- Tile area is impressions and brightness is engagement rate. The dim group is content that drew none.

Each map is a squarified treemap in the Finviz market-map language:

- group = channel, product category, or content format;
- tile = campaign, SKU, or post;
- area = resource committed (ad spend, on-hand inventory, impressions);
- fill brightness = KPI (conversion rate, sell-through, engagement rate).

Hot is the deep house green `#1B4D3E`. Cold fades toward paper `#FCFCFB`.
Cold tiles also carry a wine `#7A1F2B` stroke, a hatch, and the printed
KPI, so hot and cold are not colour alone. Each tile carries a short
label and the KPI number. A legend names area and brightness. House hues
only: wine and green. Light surface only. No third hue.

The intended accepted path of each raster is named in its prompt. A
visual change starts a new authoring pass from that prompt.

---

## 4. Hypothesized instances

The three maps do not use a provider dataset, the Data Skipping
Experiment catalog, or the committed scenario file. Tile states are
hypothesized. They exist to present the reading, not to report a scored
workload. This section's figures are outside 12.6.4's catalog / manifest
/ scenario trace.

Each figure owns its instance. Every number a later raster prints is
taken from that figure's prompt table. The column contract for those
tables is `group`, `tile_id`, `label`, `size`, `kpi`, `band`, where
`band` is `hot`, `warm`, or `cold`. A visible cold pocket is present by
construction.

---

## 5. Requirements map

| id | requirement |
| --- | --- |
| I1 | One scrolling pane; no left/right split |
| I2 | Opening paragraph, then three beats of one paragraph plus one figure |
| I3 | The four paragraphs and three captions are the locked text in §2 and §3 |
| I4 | Figure ids `signal.advertising`, `signal.ecommerce`, `signal.social` |
| I5 | Each map is a Finviz-style treemap: area is resource, brightness is KPI |
| I6 | Hot is deep green; cold fades toward paper; cold tiles also use wine stroke, hatch, and a printed rate |
| I7 | Hypothesized instance; columns `group,tile_id,label,size,kpi,band` |
| I8 | No assignment strategy, search method, or fitness is selected or recommended |
| I9 | The pane does not use *teach* or *production* |
| I10 | Rasters are deferred; the pane does not reference a missing file |
| I11 | Type is the 15px walkthrough size; the stack fills the pane |
