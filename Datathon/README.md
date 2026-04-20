# Datathon-IE

EV forecasting notebook for the Iberdrola datathon. This repository contains a single end-to-end notebook, `txt_extraction.ipynb`, that:

- ingests and parses DGT monthly vehicle-registration raw files
- builds a cleaned EV dataset with Parquet caching
- forecasts `BEV`, `OTHER_RECHARGEABLE`, and `TOTAL_RECHARGEABLE`
- evaluates multiple candidate models with rolling-origin validation
- generates pessimistic / normal / optimistic scenarios through 2031
- produces 2027 planning outputs and a lightweight macro / battery / infrastructure overlay

## Repository Contents

- `txt_extraction.ipynb`: main notebook for ingestion, preprocessing, forecasting, scenario analysis, and planning outputs
- `pyproject.toml`: lightweight environment definition for running the notebook
- `.gitignore`: standard local ignore rules

## Forecasting Scope

The notebook keeps the forecasting pipeline modular and business-oriented:

- raw EV categories are reduced to `BEV` and `OTHER_RECHARGEABLE` for forecasting
- `REEV` is merged into `OTHER_RECHARGEABLE`
- multiple statistical models are compared instead of relying on a single model family
- scenario outputs are preserved separately from the base forecast
- a 2027 planning translation is included through `CHARGING_DEMAND_EQUIVALENT`

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

## Key Outputs

Depending on the cells you run, the notebook produces:

- cleaned cached dataset in Parquet format
- monthly scenario forecasts
- annual forecast summaries
- 2027 executive summary tables
- charging-demand planning tables
- macro-overlay comparison tables and plots

Typical exported forecast artifacts are written to `Datathon_Forecasting_Outputs/`.

## Notes

- The macro / battery / charging layer is a transparent overlay on top of the statistical forecast, not a replacement for the core forecasting pipeline.
- Cleanup logic is designed to be safe: raw intermediate files are only deleted after Parquet validation succeeds.
- The notebook is designed to stay editable and presentation-friendly for datathon work rather than becoming a production package.
