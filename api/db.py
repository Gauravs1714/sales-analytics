"""Simple file storage - no database needed.
Each upload is saved in  storage/ds_<id>/data.csv  +  meta.json
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import analytics as an

ROOT = Path(os.getenv("DATA_DIR", "storage"))
ROOT.mkdir(parents=True, exist_ok=True)


def _dir(ds_id):
    return ROOT / f"ds_{int(ds_id)}"


def _write(d, name, df, types, report, uploaded_at=None):
    df.to_csv(d / "data.csv", index=False)
    (d / "meta.json").write_text(json.dumps({
        "name": name, "types": types, "report": report, "rows": len(df),
        "uploaded_at": uploaded_at or datetime.utcnow().isoformat()}))


def save_dataset(name, df, types, report):
    ids = [int(p.name[3:]) for p in ROOT.glob("ds_*") if p.name[3:].isdigit()]
    ds_id = max(ids, default=0) + 1
    d = _dir(ds_id)
    d.mkdir()
    _write(d, name, df, types, report)
    return ds_id


def _meta(ds_id):
    f = _dir(ds_id) / "meta.json"
    if not f.exists():
        raise KeyError(ds_id)
    return json.loads(f.read_text())


def list_datasets():
    out = []
    for p in ROOT.glob("ds_*"):
        if p.name[3:].isdigit() and (p / "meta.json").exists():
            m = json.loads((p / "meta.json").read_text())
            out.append({"id": int(p.name[3:]), "name": m["name"], "rows": m["rows"], "uploaded_at": m["uploaded_at"]})
    return sorted(out, key=lambda x: -x["id"])


def load_dataset(ds_id):
    m = _meta(ds_id)
    df = an.convert_types(pd.read_csv(_dir(ds_id) / "data.csv", dtype=str), m["types"])
    return df, m["types"], {"id": ds_id, "name": m["name"], "report": m["report"]}


def replace_data(ds_id, df, types):
    m = _meta(ds_id)
    _write(_dir(ds_id), m["name"], df, types, m["report"], m["uploaded_at"])


def delete_dataset(ds_id):
    shutil.rmtree(_dir(ds_id), ignore_errors=True)
