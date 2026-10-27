"""Cleaning, column-type detection and analysis. Works with ANY columns."""
import io
import re

import numpy as np
import pandas as pd

DATE_HINT = re.compile(r"date|time|day|month|year|joined|dob|created|when", re.I)
ID_HINT = re.compile(r"(^|[^a-z])(id|no|code|number|sr)$|^id[^a-z]|serial", re.I)
AGN = {"sum": "Sum", "avg": "Average", "count": "Count", "max": "Highest", "min": "Lowest"}
PANDAS_AGG = {"sum": "sum", "avg": "mean", "max": "max", "min": "min"}


# ---------------------------------------------------------------- helpers
def _f(x):
    """JSON-safe float."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return round(x, 2) if np.isfinite(x) else None


def nf(n):
    """Readable number (Indian style: L = lakh, Cr = crore)."""
    if n is None or not np.isfinite(n):
        return "-"
    a = abs(n)
    if a >= 1e7:
        return f"{n / 1e7:.2f} Cr"
    if a >= 1e5:
        return f"{n / 1e5:.2f} L"
    if a >= 100:
        return f"{round(n):,}"
    return f"{n:.2f}".rstrip("0").rstrip(".")


def _num(s):
    if not pd.api.types.is_numeric_dtype(s):
        s = s.astype(str).str.replace(r"[₹$€£,\s%]", "", regex=True)
        s = s.replace({"": np.nan, "nan": np.nan, "None": np.nan, "NaT": np.nan})
    return pd.to_numeric(s, errors="coerce")


def _date(s):
    if pd.api.types.is_datetime64_any_dtype(s):
        return s
    if pd.api.types.is_numeric_dtype(s):  # Excel serial numbers
        return pd.to_datetime(s, unit="D", origin="1899-12-30", errors="coerce")
    s = s.astype(str).str.strip().replace({"": None, "nan": None, "None": None})
    return pd.to_datetime(s, errors="coerce", dayfirst=True, format="mixed")


def detect_type(name, s):
    """Return one of: num, date, cat, id."""
    ne = s.dropna()
    if ne.dtype == object:
        ne = ne[ne.astype(str).str.strip() != ""]
    if ne.empty:
        return "cat"
    uniq = ne.nunique()
    if pd.api.types.is_datetime64_any_dtype(s):
        return "date"
    if pd.api.types.is_numeric_dtype(s):
        if DATE_HINT.search(name) and ne.between(20000, 80000).all():
            return "date"
        return "id" if ID_HINT.search(name) and uniq == len(ne) else "num"
    txt = ne.astype(str)
    if txt.str.contains(r"[-/]|[A-Za-z]{3}").mean() >= 0.8 and _date(txt).notna().mean() >= 0.8:
        return "date"
    if _num(txt).notna().mean() >= 0.8:
        return "id" if ID_HINT.search(name) and uniq == len(ne) else "num"
    if uniq > 40 and uniq > 0.5 * len(ne):
        return "id"
    return "cat"


def convert_types(df, types):
    df = df.copy()
    for c, t in types.items():
        if c not in df:
            continue
        if t == "num":
            df[c] = _num(df[c])
        elif t == "date":
            df[c] = _date(df[c])
        else:
            df[c] = df[c].fillna("(blank)").astype(str).str.strip()
    return df


def read_file(name, raw):
    if name.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(raw), encoding_errors="replace")
    return pd.read_excel(io.BytesIO(raw))


def clean(df):
    """Clean any dataframe. Returns (clean_df, column_types, report)."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    report = {"rows_read": int(len(df))}
    df = df.replace(r"^\s*$", np.nan, regex=True)
    n = len(df)
    df = df.dropna(how="all")
    report["empty_removed"] = int(n - len(df))
    n = len(df)
    df = df.drop_duplicates()
    report["duplicates_removed"] = int(n - len(df))
    types = {c: detect_type(c, df[c]) for c in df.columns}
    df = convert_types(df, types).reset_index(drop=True)
    report["rows_loaded"] = int(len(df))
    report["columns"] = {t: sum(v == t for v in types.values()) for t in ("num", "date", "cat", "id")}
    return df, types, report


def describe_columns(df, types):
    out = []
    for c, t in types.items():
        item = {"name": c, "type": t, "unique": int(df[c].nunique()), "missing": int(df[c].isna().sum())}
        if t == "cat" and item["unique"] <= 30:
            item["values"] = sorted(df[c].dropna().astype(str).unique().tolist())
        if t == "date":
            item["months"] = sorted(df[c].dropna().dt.strftime("%Y-%m").unique().tolist())
        out.append(item)
    return out


# ---------------------------------------------------------------- analysis
def apply_filters(df, filters, date_col=None, date_from=None, date_to=None):
    for col, vals in (filters or {}).items():
        if col in df and vals:
            df = df[df[col].isin(vals)]
    if date_col and date_col in df and (date_from or date_to):
        m = df[date_col].dt.strftime("%Y-%m")
        if date_from:
            df = df[m >= date_from]
            m = df[date_col].dt.strftime("%Y-%m")
        if date_to:
            df = df[m <= date_to]
    return df


def period_key(s, grain):
    return s.dt.strftime({"year": "%Y", "month": "%Y-%m", "day": "%Y-%m-%d"}[grain])


def aggregate(df, by, measure, agg):
    if agg == "count" or not measure:
        return df.groupby(by).size()
    return df.groupby(by)[measure].agg(PANDAS_AGG[agg])


def next_periods(last, grain, n):
    if grain == "year":
        return [str(int(last) + i) for i in range(1, n + 1)]
    if grain == "month":
        return [str(p) for p in pd.period_range(pd.Period(last, "M") + 1, periods=n, freq="M")]
    return [d.strftime("%Y-%m-%d") for d in pd.date_range(pd.Timestamp(last) + pd.Timedelta(days=1), periods=n)]


def forecast_linear(values, n):
    x = np.arange(len(values))
    slope, icpt = np.polyfit(x, values, 1)
    fut = icpt + slope * np.arange(len(values), len(values) + n)
    return np.clip(fut, 0, None) if (np.asarray(values) >= 0).all() else fut


def correlation_matrix(df, types, cols=None):
    cols = cols or [c for c, t in types.items() if t == "num"][:8]
    if len(cols) < 2:
        return {"columns": cols, "matrix": []}
    m = df[cols].corr().round(2)
    return {"columns": cols, "matrix": [[_f(v) for v in row] for row in m.values]}


def summarize(df, types, p):
    m = p.get("measure") or None
    ag = (p.get("agg") or "sum") if m else "count"
    g, sp, d = p.get("group_by"), p.get("split_by"), p.get("date_col")
    grain = p.get("grain") or "month"
    n_fc = int(p.get("forecast") or 0)
    target = float(p.get("target") or 0)
    df = apply_filters(df, p.get("filters"), d, p.get("date_from"), p.get("date_to"))
    label = "Count of rows" if ag == "count" else f"{AGN[ag]} of {m}"
    vals = df[m].dropna() if m else pd.Series(dtype=float)

    kpis = {"records": int(len(df)), "total": None, "average": None, "highest": None, "change_pct": None}
    if m and len(vals):
        kpis.update(total=_f(vals.sum()), average=_f(vals.mean()), highest=_f(vals.max()))

    trend = {"periods": [], "values": [], "forecast_periods": [], "forecast_values": [],
             "target": target, "met": 0, "below": []}
    ts = None
    if d and d in df and df[d].notna().any():
        sub = df[df[d].notna()]
        ts = aggregate(sub, period_key(sub[d], grain), m, ag).sort_index()
        trend["periods"] = [str(i) for i in ts.index]
        trend["values"] = [_f(v) for v in ts.values]
        if len(ts) > 1 and ts.iloc[-2]:
            kpis["change_pct"] = _f((ts.iloc[-1] - ts.iloc[-2]) / abs(ts.iloc[-2]) * 100)
        if n_fc and len(ts) >= 3:
            trend["forecast_periods"] = next_periods(trend["periods"][-1], grain, n_fc)
            trend["forecast_values"] = [_f(v) for v in forecast_linear(ts.values, n_fc)]
        if target:
            trend["met"] = int((ts >= target).sum())
            trend["below"] = [str(i) for i in ts.index[ts < target]]

    groups, gs = [], None
    if g and g in df:
        gs = aggregate(df, g, m, ag).sort_values(ascending=False)
        groups = [{"name": str(k), "value": _f(v)} for k, v in gs.head(8).items()]

    split = []
    if sp and sp in df:
        ss = aggregate(df, sp, m, "count" if ag == "count" else "sum").sort_values(ascending=False)
        split = [{"name": str(k), "value": _f(v)} for k, v in ss.head(5).items()]
        if len(ss) > 5:
            split.append({"name": "Other", "value": _f(ss.iloc[5:].sum())})

    hist = {"edges": [], "counts": []}
    if len(vals) > 1:
        counts, edges = np.histogram(vals, bins=10)
        hist = {"edges": [_f(e) for e in edges], "counts": counts.tolist()}

    return {"label": label, "measure": m, "agg": ag, "records": int(len(df)), "kpis": kpis,
            "trend": trend, "groups": groups, "split": split, "histogram": hist,
            "insights": make_insights(df, types, m, ag, g, grain, label, vals, ts, gs, trend, target)}


def make_insights(df, types, m, ag, g, grain, label, vals, ts, gs, trend, target):
    out = []
    if gs is not None and len(gs) > 1:
        tot = gs.sum()
        if ag in ("sum", "count") and tot:
            out.append(f"**{gs.index[0]}** leads {g} with {gs.iloc[0] / tot * 100:.0f}% of the total. "
                       f"The top 3 together make up {gs.iloc[:3].sum() / tot * 100:.0f}%.")
        else:
            out.append(f"**{gs.index[0]}** has the highest {label.lower()} ({nf(gs.iloc[0])}) and "
                       f"**{gs.index[-1]}** the lowest ({nf(gs.iloc[-1])}).")
    if ts is not None and len(ts) > 1:
        out.append(f"Best {grain}: **{ts.idxmax()}** ({nf(ts.max())}). Lowest: **{ts.idxmin()}** ({nf(ts.min())}).")
        a, b = ts.iloc[-2], ts.iloc[-1]
        if a:
            out.append(f"The latest {grain} ({ts.index[-1]}) is {abs((b - a) / abs(a) * 100):.1f}% "
                       f"{'higher' if b >= a else 'lower'} than the one before.")
    if trend["forecast_periods"]:
        fp, fv = trend["forecast_periods"], trend["forecast_values"]
        out.append(f"If the recent trend continues, **{fp[0]}** will be about **{nf(fv[0])}** "
                   f"and {fp[-1]} about {nf(fv[-1])}.")
    if target and ts is not None:
        below = trend["below"]
        extra = f" Below target: {', '.join(below[:4])}" + (f" and {len(below) - 4} more" if len(below) > 4 else "") + "." if below else ""
        out.append(f"The target of {nf(target)} was met in **{trend['met']} of {len(ts)}** {grain}s." + extra)
    if m and len(vals) > 20:
        sd = vals.std()
        hi = int((vals > vals.mean() + 3 * sd).sum()) if sd else 0
        if hi:
            out.append(f"{hi} record(s) in {m} look unusually high (over 3 standard deviations above average). "
                       "Check them before trusting the totals.")
    nums = [c for c, t in types.items() if t == "num"][:8]
    if len(nums) > 1 and len(df) > 2:
        cm = df[nums].corr()
        c = cm.abs().values.copy()
        np.fill_diagonal(c, 0)
        if np.nanmax(c) >= 0.6:
            a, b = np.unravel_index(np.nanargmax(c), c.shape)
            r = cm.iloc[a, b]
            out.append(f"**{nums[a]}** and **{nums[b]}** show a {'strong' if abs(r) >= .7 else 'moderate'} "
                       f"{'positive' if r > 0 else 'negative'} link (r = {r:.2f}).")
    for col in df.columns:
        miss = df[col].isna().mean() if len(df) else 0
        if miss > 0.1:
            out.append(f"{col} is missing in {miss * 100:.0f}% of rows.")
    return out[:8] or ["Not enough data for insights yet."]


def fill_missing(df, types, mode):
    """How to treat empty numbers: keep | zero | mean | drop."""
    nums = [c for c, t in types.items() if t == "num"]
    if mode == "keep" or not nums:
        return df
    if mode == "drop":
        return df.dropna(subset=nums)
    df = df.copy()
    for c in nums:
        df[c] = df[c].fillna(0 if mode == "zero" else df[c].mean())
    return df


def add_calc_column(df, types, a, op, b, name):
    """New numeric column = a (op) b. Returns (df, types). Raises ValueError on bad input."""
    if types.get(a) != "num" or types.get(b) != "num":
        raise ValueError("Both columns must be numeric")
    name = (name or "").strip()
    if not name or name in df.columns:
        raise ValueError("Choose a new column name that is not used yet")
    x, y = df[a], df[b]
    if op == "*":
        res = x * y
    elif op == "+":
        res = x + y
    elif op == "-":
        res = x - y
    elif op == "/":
        res = x / y.where(y != 0)
    else:
        raise ValueError("Operation must be one of * + - /")
    df = df.copy()
    df[name] = pd.to_numeric(res, errors="coerce")
    return df, {**types, name: "num"}


def relationship(df, types, x=None, y=None):
    out = {"correlations": correlation_matrix(df, types), "points": [], "r": None}
    if x and y and x != y and x in df and y in df:
        pts = df[[x, y]].dropna()
        if len(pts) > 1:
            out["r"] = _f(pts[x].corr(pts[y]))
            if len(pts) > 1000:
                pts = pts.sample(1000, random_state=1)
            out["points"] = pts.values.tolist()
    return out


def pivot(df, row, col, measure, agg):
    """Excel-style pivot table with totals."""
    if not row or row not in df:
        return pd.DataFrame()
    if agg == "count" or not measure:
        t = pd.crosstab(df[row], df[col], margins=True, margins_name="Total") if col else df.groupby(row).size().to_frame("Count")
    elif col:
        t = pd.pivot_table(df, index=row, columns=col, values=measure, aggfunc=PANDAS_AGG[agg],
                           fill_value=0, margins=True, margins_name="Total")
    else:
        t = df.groupby(row)[measure].agg(PANDAS_AGG[agg]).to_frame(f"{AGN[agg]} of {measure}")
    return t.round(2)


def report_xlsx(df, summary):
    """Excel report: Summary, By group, Trend, Data."""
    k, t = summary["kpis"], summary["trend"]
    rows = [["Report", summary["label"]], ["Records in view", summary["records"]]]
    rows += [[n, v] for n, v in (("Total", k["total"]), ("Average", k["average"]), ("Highest", k["highest"]),
                                  ("Change vs previous period (%)", k["change_pct"])) if v is not None]
    rows += [[], ["Insights"]] + [[s.replace("**", "")] for s in summary["insights"]]
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pd.DataFrame(rows).to_excel(xw, sheet_name="Summary", header=False, index=False)
        if summary["groups"]:
            pd.DataFrame(summary["groups"]).to_excel(xw, sheet_name="By group", index=False)
        if t["periods"]:
            tr = pd.DataFrame({"period": t["periods"], "value": t["values"]})
            if t["target"]:
                tr["target"] = t["target"]
                tr["target_met"] = np.where(tr["value"] >= t["target"], "Yes", "No")
            if t["forecast_periods"]:
                tr = pd.concat([tr, pd.DataFrame({"period": [x + " (forecast)" for x in t["forecast_periods"]],
                                                  "value": t["forecast_values"]})])
            tr.to_excel(xw, sheet_name="Trend", index=False)
        out = df.copy()
        for c in out.select_dtypes("datetime").columns:
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        out.to_excel(xw, sheet_name="Data", index=False)
        for ws in xw.book.worksheets:
            for col in ws.columns:
                width = max(len(str(c.value or "")) for c in list(col)[:50]) + 2
                ws.column_dimensions[col[0].column_letter].width = min(40, max(10, width))
    return buf.getvalue()
