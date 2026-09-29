"""Build the versioned tree seed from the raw Milan tree census.

Source: Comune di Milano, dataset ds2484 "Alberi - localizzazione"
(https://dati.comune.milano.it/dataset/ds2484_infogeo_alberi_localizzazione),
extraction of 2025-03-31. Licence: to be verified on the dataset page.
Only municipal trees are in the census (no private trees).

Input (not versioned, data_milan/raw/ is gitignored):
    data_milan/raw/trees/ds2484_alberi_20250331.csv   (delimiter ';')
Output (versioned, a few MB):
    data_milan/seeds/trees/alberi_milano_20250331.csv.gz
    columns: tree_id (obj_id), genus, species, height_m, crown_diameter_m, lon, lat

No filtering here: plausibility filters live in models/staging/milan/
stg_milan_trees.sql (and are mirrored in solar_exposure.py).
"""

import csv
import gzip
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RAW_CSV = PROJECT_ROOT / "data_milan/raw/trees/ds2484_alberi_20250331.csv"
OUTPUT = PROJECT_ROOT / "data_milan/seeds/trees/alberi_milano_20250331.csv.gz"


def _num(value: str) -> str:
    """Decimal-comma tolerant; '' stays '' (missing)."""
    return value.strip().replace(",", ".")


def _coord(value: str) -> str:
    v = _num(value)
    return f"{float(v):.6f}" if v else ""


def main() -> None:
    n = 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_CSV, newline="", encoding="utf-8-sig") as src, gzip.GzipFile(
        OUTPUT, "wb", mtime=0
    ) as raw_out:
        import io

        out = io.TextIOWrapper(raw_out, encoding="utf-8", newline="")
        writer = csv.writer(out)
        writer.writerow(["tree_id", "genus", "species", "height_m", "crown_diameter_m", "lon", "lat"])
        for row in csv.DictReader(src, delimiter=";"):
            writer.writerow(
                [
                    row["obj_id"].strip(),
                    row["genere"].strip(),
                    row["specie"].strip(),
                    _num(row["h_m"]),
                    _num(row["diam_chiom"]),
                    _coord(row["LONG_X_4326"]),
                    _coord(row["LAT_Y_4326"]),
                ]
            )
            n += 1
        out.flush()
        out.detach()
    print(f"Wrote {n} trees to {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
