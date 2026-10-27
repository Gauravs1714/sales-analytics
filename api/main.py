"""FastAPI backend. Run:  uvicorn api.main:app --reload"""
import json
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import analytics as an
from . import db

app = FastAPI(title="Sales Analytics API", version="2.0",
              description="Upload any Excel/CSV and get KPIs, trends, forecast and insights.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
CACHE = {}


def get(ds_id):
    if ds_id not in CACHE:
        try:
            CACHE[ds_id] = db.load_dataset(ds_id)
        except KeyError:
            raise HTTPException(404, "Dataset not found")
    return CACHE[ds_id]


def parse_filters(raw):
    try:
        f = json.loads(raw or "{}")
        assert isinstance(f, dict)
        return f
    except Exception:
        raise HTTPException(400, 'filters must be a JSON object, e.g. {"Region": ["North"]}')


def check_cols(df, *cols):
    for c in cols:
        if c and c not in df.columns:
            raise HTTPException(400, f"Unknown column: {c}")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    raw = await file.read()
    try:
        df = an.read_file(file.filename or "data.csv", raw)
    except Exception as e:
        raise HTTPException(400, f"Could not read the file. Upload .xlsx, .xls or .csv. ({e})")
    if df.empty or len(df.columns) == 0:
        raise HTTPException(400, "The file has no data. Add a header row and some rows.")
    clean, types, report = an.clean(df)
    if clean.empty:
        raise HTTPException(400, "No rows were left after cleaning.")
    ds_id = db.save_dataset(file.filename, clean, types, report)
    CACHE[ds_id] = (clean, types, {"id": ds_id, "name": file.filename, "report": report})
    return {"id": ds_id, "name": file.filename, "report": report, "types": types}


@app.get("/datasets")
def datasets():
    return db.list_datasets()


@app.delete("/datasets/{ds_id}")
def remove(ds_id: int):
    db.delete_dataset(ds_id)
    CACHE.pop(ds_id, None)
    return {"deleted": ds_id}


@app.get("/datasets/{ds_id}/columns")
def columns(ds_id: int):
    df, types, meta = get(ds_id)
    return {"name": meta["name"], "rows": len(df), "columns": an.describe_columns(df, types)}


@app.get("/datasets/{ds_id}/summary")
def summary(ds_id: int, measure: Optional[str] = None, agg: str = "sum", group_by: Optional[str] = None,
            split_by: Optional[str] = None, date_col: Optional[str] = None, grain: str = "month",
            target: float = 0, forecast: int = 0, date_from: Optional[str] = None,
            date_to: Optional[str] = None, filters: str = "{}"):
    df, types, _ = get(ds_id)
    check_cols(df, measure, group_by, split_by, date_col)
    if agg not in an.AGN or grain not in ("day", "month", "year"):
        raise HTTPException(400, "Bad agg or grain")
    p = dict(measure=measure, agg=agg, group_by=group_by, split_by=split_by, date_col=date_col, grain=grain,
             target=target, forecast=forecast, date_from=date_from, date_to=date_to, filters=parse_filters(filters))
    return an.summarize(df, types, p)


@app.get("/datasets/{ds_id}/data")
def data(ds_id: int, limit: int = 500, date_col: Optional[str] = None, date_from: Optional[str] = None,
         date_to: Optional[str] = None, filters: str = "{}"):
    df, types, _ = get(ds_id)
    df = an.apply_filters(df, parse_filters(filters), date_col, date_from, date_to).head(limit).copy()
    for c in df.select_dtypes("datetime").columns:
        df[c] = df[c].dt.strftime("%Y-%m-%d")
    return {"columns": list(df.columns), "rows": json.loads(df.to_json(orient="values"))}


@app.get("/datasets/{ds_id}/relationship")
def relationship(ds_id: int, x: Optional[str] = None, y: Optional[str] = None, date_col: Optional[str] = None,
                 date_from: Optional[str] = None, date_to: Optional[str] = None, filters: str = "{}"):
    df, types, _ = get(ds_id)
    check_cols(df, x, y)
    df = an.apply_filters(df, parse_filters(filters), date_col, date_from, date_to)
    return an.relationship(df, types, x, y)


class CalcIn(BaseModel):
    a: str
    op: str
    b: str
    name: str


@app.post("/datasets/{ds_id}/calc")
def calc(ds_id: int, body: CalcIn):
    df, types, meta = get(ds_id)
    check_cols(df, body.a, body.b)
    try:
        df, types = an.add_calc_column(df, types, body.a, body.op, body.b, body.name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.replace_data(ds_id, df, types)
    CACHE[ds_id] = (df, types, meta)
    return {"added": body.name}


@app.get("/datasets/{ds_id}/export")
def export(ds_id: int, kind: str = "xlsx", params: str = "{}"):
    df, types, _ = get(ds_id)
    p = parse_filters(params)
    p.setdefault("filters", {})
    view = an.apply_filters(df, p["filters"], p.get("date_col"), p.get("date_from"), p.get("date_to"))
    if kind == "csv":
        return Response(view.to_csv(index=False), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=cleaned-data.csv"})
    res = an.summarize(df, types, p)
    return Response(an.report_xlsx(view, res),
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": "attachment; filename=analytics-report.xlsx"})
