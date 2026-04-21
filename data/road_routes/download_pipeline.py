"""
Road Routes (Rutas por Carretera) Download & Clean Pipeline
Source: Spanish Ministry of Transport (MITMA) Open Data
S3 Bucket: https://movilidad-opendata.mitma.es/estudios_rutas/

Dataset Structure:
  od_rutas/              - Origin-Destination matrices per road route (~40 MB/file compressed)
  informacion_tramo/     - Aggregated trip counts per road segment (~10 MB/file compressed)
  geometria/             - Road segment geometries (Shapefile + CSV, ~191 MB total)
  tramo_ruta/            - Segment-route relations (HUGE: ~1.5 GB/file compressed, opt-in only)

Available dates: 2023-08-26, 2023-08-29, 2023-10-11..22, 2024-03-31, 2024-08-24/27, 2024-10-16/19
"""

import gzip
import shutil
import requests
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://movilidad-opendata.mitma.es/estudios_rutas"
OUTPUT_DIR = Path(__file__).parent  # same folder as this script

# All available dates (YYYYMMDD strings)
ALL_DATES = [
    "20230826", "20230829",
    "20231011", "20231012", "20231016", "20231017",
    "20231020", "20231021", "20231022",
    "20240331",
    "20240824", "20240827",
    "20241016", "20241019",
]

# Default: download everything except the massive tramo_ruta files
# Set DOWNLOAD_TRAMO_RUTA = True to include them (~1.5 GB compressed each!)
DOWNLOAD_TRAMO_RUTA = False

# Limit which dates to download (None = all dates)
# Example: DATES_FILTER = ["20240331", "20241016"]
DATES_FILTER = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def download_file(url: str, dest_path: Path, chunk_size: int = 1024 * 1024) -> bool:
    """Stream-download a file with a progress bar. Returns True on success."""
    try:
        r = requests.get(url, stream=True, timeout=60)
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f, tqdm(
            desc=dest_path.name,
            total=total,
            unit="B",
            unit_scale=True,
            leave=False,
        ) as bar:
            for chunk in r.iter_content(chunk_size=chunk_size):
                f.write(chunk)
                bar.update(len(chunk))
        return True
    except requests.HTTPError as e:
        print(f"  [SKIP] {url} — {e}")
        return False


def decompress_gz(gz_path: Path, out_path: Path) -> Path:
    """Decompress a .gz file; returns the decompressed path."""
    with gzip.open(gz_path, "rb") as f_in, open(out_path, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    gz_path.unlink()  # remove compressed file after extraction
    return out_path


# ---------------------------------------------------------------------------
# Cleaning functions
# ---------------------------------------------------------------------------

def clean_od_rutas(df: pd.DataFrame) -> pd.DataFrame:
    """
    OD Routes file — pipe-separated (|)
    Columns: date | origen | destino | ruta | distancia | viajes
    Cleans: drops nulls on key fields, casts numeric columns, renames to English.
    """
    rename_map = {
        "date":      "date",
        "origen":    "origin_zone",
        "destino":   "destination_zone",
        "ruta":      "route_id",
        "distancia": "distance_km",
        "viajes":    "trips",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    key_cols = [c for c in ["origin_zone", "destination_zone", "route_id"] if c in df.columns]
    df = df.dropna(subset=key_cols)

    for col in ["distance_km", "trips"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Parse date column if present
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], format="%Y%m%d", errors="coerce")

    df = df.reset_index(drop=True)
    return df


def clean_tramos_info(df: pd.DataFrame) -> pd.DataFrame:
    """
    Segment info file — semicolon-separated (;)
    Columns: tramo | total | origen_principal | destino_principal | corto | medio | largo |
             intra_GAU | inter_GAU | intra_provincial | inter_provincial |
             intra_ccaa | inter_ccaa | nacional | extranjero
    Cleans: drops nulls on segment id, casts all numeric columns, renames to English.
    """
    rename_map = {
        "tramo":              "segment_id",
        "total":              "trips_total",
        "origen_principal":   "main_origin",
        "destino_principal":  "main_destination",
        "corto":              "trips_short",
        "medio":              "trips_medium",
        "largo":              "trips_long",
        "intra_GAU":          "trips_intra_gau",
        "inter_GAU":          "trips_inter_gau",
        "intra_provincial":   "trips_intra_provincial",
        "inter_provincial":   "trips_inter_provincial",
        "intra_ccaa":         "trips_intra_ccaa",
        "inter_ccaa":         "trips_inter_ccaa",
        "nacional":           "trips_national",
        "extranjero":         "trips_foreign",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    if "segment_id" in df.columns:
        df = df.dropna(subset=["segment_id"])

    numeric_cols = [
        "trips_total", "trips_short", "trips_medium", "trips_long",
        "trips_intra_gau", "trips_inter_gau", "trips_intra_provincial",
        "trips_inter_provincial", "trips_intra_ccaa", "trips_inter_ccaa",
        "trips_national", "trips_foreign",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.reset_index(drop=True)
    return df


def clean_tramo_ruta(df: pd.DataFrame) -> pd.DataFrame:
    """
    Segment-route relation file — detect separator automatically.
    Minimal cleaning: drop null keys, cast numeric.
    """
    key_cols = [c for c in ["origen", "destino", "ruta", "tramo"] if c in df.columns]
    if key_cols:
        df = df.dropna(subset=key_cols)
    if "viajes" in df.columns:
        df["viajes"] = pd.to_numeric(df["viajes"], errors="coerce")
    df = df.reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# Geometry download (shapefile + validation CSV)
# ---------------------------------------------------------------------------

GEOMETRY_FILES = [
    "Geometria_tramos.cpg",
    "Geometria_tramos.dbf",
    "Geometria_tramos.prj",
    "Geometria_tramos.shp",
    "Geometria_tramos.shx",
    "rt_tramo_val.csv",
]
GEOMETRY_PREFIX = f"{BASE_URL}/geometria/Geometria_tramos_2023_2024"


def download_geometry():
    geo_dir = OUTPUT_DIR / "geometria"
    geo_dir.mkdir(exist_ok=True)
    print("\n--- Geometry ---")
    for fname in GEOMETRY_FILES:
        dest = geo_dir / fname
        if dest.exists():
            print(f"  [EXISTS] {fname}")
            continue
        print(f"  Downloading {fname} ...")
        download_file(f"{GEOMETRY_PREFIX}/{fname}", dest)
    print("  Geometry done.")


# ---------------------------------------------------------------------------
# Per-date dataset downloader
# ---------------------------------------------------------------------------

def download_and_clean_date(date: str):
    """Download, decompress, clean, and save all per-date files for one date."""

    datasets = [
        {
            "subdir":   "od_rutas",
            "gz_name":  f"{date}_OD_rutas.csv.gz",
            "out_name": f"{date}_OD_rutas.csv",
            "sep":      "|",
            "cleaner":  clean_od_rutas,
        },
        {
            "subdir":   "informacion_tramo",
            "gz_name":  f"{date}_Tramos_info_odmatrix.csv.gz",
            "out_name": f"{date}_Tramos_info_odmatrix.csv",
            "sep":      ";",
            "cleaner":  clean_tramos_info,
        },
    ]

    if DOWNLOAD_TRAMO_RUTA:
        datasets.append({
            "subdir":   "tramo_ruta",
            "gz_name":  f"{date}_Relaciones_tramos_rutas.csv.gz",
            "out_name": f"{date}_Relaciones_tramos_rutas.csv",
            "sep":      "|",
            "cleaner":  clean_tramo_ruta,
        })

    for ds in datasets:
        out_dir = OUTPUT_DIR / ds["subdir"]
        out_dir.mkdir(exist_ok=True)
        out_csv = out_dir / ds["out_name"]

        if out_csv.exists():
            print(f"  [EXISTS] {ds['out_name']}")
            continue

        gz_path = out_dir / ds["gz_name"]
        url = f"{BASE_URL}/{ds['subdir']}/{ds['gz_name']}"

        print(f"  Downloading {ds['gz_name']} ...")
        ok = download_file(url, gz_path)
        if not ok:
            continue

        print(f"  Decompressing ...")
        raw_csv = out_dir / ds["out_name"].replace(".csv", "_raw.csv")
        decompress_gz(gz_path, raw_csv)

        print(f"  Cleaning ...")
        df = pd.read_csv(raw_csv, sep=ds["sep"], low_memory=False)
        df = ds["cleaner"](df)
        df.to_csv(out_csv, index=False)
        raw_csv.unlink()

        print(f"  Saved {out_csv.name}  ({len(df):,} rows)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dates = DATES_FILTER if DATES_FILTER else ALL_DATES
    print(f"Road Routes Pipeline — {len(dates)} date(s) to process")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Include tramo_ruta (very large): {DOWNLOAD_TRAMO_RUTA}\n")

    for date in dates:
        print(f"\n=== {date} ===")
        download_and_clean_date(date)

    download_geometry()
    print("\nAll done.")


if __name__ == "__main__":
    main()
