# Datathon-IE

EV forecasting notebook for the Iberdrola datathon. This repository contains a single end-to-end notebook, `txt_extraction.ipynb`, that:

- ingests and parses DGT monthly vehicle-registration raw files
- builds a cleaned EV dataset with Parquet caching
- forecasts `BEV`, `OTHER_RECHARGEABLE`, `TOTAL_RECHARGEABLE`, `TOTAL_ALL_CARS`, and `ELECTRIFIED_TOTAL`
- derives `NORMAL_CARS = TOTAL_ALL_CARS - ELECTRIFIED_TOTAL`
- evaluates multiple candidate models with rolling-origin validation
- generates pessimistic / normal / optimistic scenarios through 2031
- produces 2027 planning outputs and a lightweight macro / battery / infrastructure overlay

## Repository Contents

- `txt_extraction.ipynb`: main notebook for ingestion, preprocessing, forecasting, scenario analysis, and planning outputs
- `pyproject.toml`: lightweight environment definition for running the notebook
- `environment.yml`: optional Conda-style environment file
- `uv.lock`: locked dependency snapshot for `uv`
- `Datathon_Forecasting_Outputs/`: exported CSV outputs written by the notebook
- `.gitignore`: standard local ignore rules

## Forecasting Scope

The notebook keeps the forecasting pipeline modular and business-oriented:

- raw EV categories are reduced to `BEV` and `OTHER_RECHARGEABLE` for forecasting
- `REEV` is merged into `OTHER_RECHARGEABLE`
- market-level baselines for all cars and electrified cars are modelled alongside the EV series
- `NORMAL_CARS` is derived from the total-car and electrified forecasts instead of being forecast independently
- multiple statistical models are compared instead of relying on a single model family
- scenario outputs are preserved separately from the base forecast
- a 2027 planning translation is included through `CHARGING_DEMAND_EQUIVALENT`
- a macro / battery affordability overlay is layered on top of the statistical forecast for scenario storytelling

## Environment Setup

This repo is configured for Python `>=3.12,<3.13`.

Using `uv`:

```bash
uv sync
uv run python -m ipykernel install --user --name datathon-notebook
```

Or with a regular virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

If you prefer not to install the project itself, install the dependencies listed in `pyproject.toml` manually.

## Running the Notebook

1. Open `txt_extraction.ipynb` in Jupyter or Colab.
2. Review the **Configurable Parameters** cell first.
3. Run the notebook from top to bottom.
4. If a validated Parquet cache already exists, the notebook can skip the heavy raw-download / reparsing path.

## Visual Outputs

The notebook is designed to be presentation-friendly, not just analytical. In addition to the forecast tables, it now includes:

- workflow / pipeline overview near the top of the notebook
- rechargeable-market composition and growth visuals
- model-ranking charts after rolling-origin validation
- monthly forecast panels for EV demand, total cars, and normal cars
- a forecasted car-mix pie chart for the focused year / scenario
- rechargeable-share-of-total-market lines extended through the forecast horizon
- scenario overlay comparisons and 2027 waterfall-style planning views
- charging-weight sensitivity charts
- a compact executive dashboard tying demand, model fit, scenario spread, and planning together

## Key Outputs

Depending on the cells you run, the notebook produces:

- cleaned cached dataset in Parquet format
- monthly scenario forecasts
- annual forecast summaries
- 2027 executive summary tables
- charging-demand planning tables
- macro-overlay comparison tables and plots
- total-car / normal-car market summaries
- presentation-ready figures used directly in the final notebook narrative

Typical exported forecast artifacts are written to `Datathon_Forecasting_Outputs/`.

## Notes

- The macro / battery / charging layer is a transparent overlay on top of the statistical forecast, not a replacement for the core forecasting pipeline.
- Cleanup logic is designed to be safe: raw intermediate files are only deleted after Parquet validation succeeds.
- A very small number of legacy rows exist before the main modern coverage window. Those rows are useful for audit transparency, but market-level visuals are mainly interpreted from the stronger post-2018 history.
- The notebook is designed to stay editable and presentation-friendly for datathon work rather than becoming a production package.
