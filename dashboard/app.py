"""Analytics Studio - one-file Streamlit app. No separate server is needed.
Run from the project root:  streamlit run dashboard/app.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402

import sample_data  # noqa: E402
from api import analytics as an  # noqa: E402

PALETTES = {
    "Neon": ["#8B5CF6", "#06B6D4", "#F472B6", "#FBBF24", "#34D399", "#60A5FA", "#FB7185"],
    "Sunset": ["#F97316", "#EC4899", "#FACC15", "#EF4444", "#A855F7", "#FB923C", "#F43F5E"],
    "Ocean": ["#0EA5E9", "#14B8A6", "#6366F1", "#22D3EE", "#38BDF8", "#2DD4BF", "#818CF8"],
    "Forest": ["#22C55E", "#EAB308", "#10B981", "#84CC16", "#F59E0B", "#14B8A6", "#A3E635"],
}
AGG = {"sum": "Sum", "avg": "Average", "count": "Count of rows", "max": "Highest", "min": "Lowest"}
MISSING = {"keep": "Leave empty", "zero": "Fill with 0", "mean": "Fill with average", "drop": "Remove those rows"}
nf = an.nf

st.set_page_config(page_title="Analytics Studio", page_icon="📊", layout="wide")
S = st.session_state
S.setdefault("data", {})      # dataset id -> {name, df, types, report}  (private to each visitor)
S.setdefault("next_id", 1)


def add_dataset(name, raw):
    try:
        df = an.read_file(name, raw)
    except Exception as e:
        st.sidebar.error(f"Could not read this file. Upload .xlsx, .xls or .csv. ({e})")
        return
    if df.empty or len(df.columns) == 0:
        st.sidebar.error("The file has no data. Add a header row and some rows.")
        return
    clean, types, report = an.clean(df, drop_duplicates=False)
    if clean.empty:
        st.sidebar.error("No rows were left after cleaning.")
        return
    i = S.next_id
    S.next_id += 1
    S.data[i] = {"name": name, "df": clean, "types": types, "report": report}
    S.ds, S.report = i, report
    st.rerun()


def sel(label, options, key, default=None, **kw):
    """selectbox that remembers its value per dataset."""
    if key in S:
        return st.selectbox(label, options, key=key, **kw)
    return st.selectbox(label, options, index=options.index(default) if default in options else 0, key=key, **kw)


def pick(arr, rx):
    return next((a for a in arr if re.search(rx, a, re.I)), arr[0] if arr else None)


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("## 📊 Analytics Studio")
    theme = st.selectbox("🎨 Colour theme", list(PALETTES))
    P = PALETTES[theme]
    st.markdown(f"""<style>
    .hero{{background:linear-gradient(120deg,{P[0]},{P[2]} 55%,{P[1]});padding:26px 30px;border-radius:18px;margin-bottom:18px;box-shadow:0 10px 30px {P[0]}55}}
    .hero h1{{margin:0;font-size:30px;color:#fff;padding:0}} .hero p{{margin:4px 0 0;color:#ffffffD9}}
    .kpi{{border-radius:16px;padding:16px 18px;color:#fff;text-shadow:0 1px 3px #0006;box-shadow:0 6px 18px #0005}}
    .kpi span{{display:block;font-size:13px;opacity:.92}} .kpi b{{font-size:26px;font-weight:700}}
    .ins{{background:#151B33;border-radius:12px;padding:10px 14px;margin:6px 0;color:#E8ECFF}}
    .step{{background:#151B33;border-radius:14px;padding:16px;height:100%}} .step b{{color:{P[1]}}}
    div[data-baseweb="tab-list"]{{gap:6px}} button[data-baseweb="tab"]{{border-radius:10px 10px 0 0;padding:8px 16px}}
    button[data-baseweb="tab"][aria-selected="true"]{{background:{P[0]}33;border-bottom:3px solid {P[0]}}}
    </style>""", unsafe_allow_html=True)

    st.markdown("### 1. Data")
    up = st.file_uploader("Upload Excel or CSV", type=["xlsx", "xls", "csv"])
    if up is not None and S.get("last_up") != (up.name, up.size):
        S.last_up = (up.name, up.size)
        add_dataset(up.name, up.getvalue())
    c1, c2 = st.columns(2)
    if c1.button("Sales sample"):
        add_dataset("sample_sales.csv", sample_data.sales_df().to_csv(index=False).encode())
    if c2.button("Staff sample"):
        add_dataset("sample_staff.csv", sample_data.staff_df().to_csv(index=False).encode())
    with st.expander("Need a sample file to test?"):
        st.download_button("⬇ sample_sales.csv", sample_data.sales_df().to_csv(index=False), "sample_sales.csv", "text/csv")
        st.download_button("⬇ sample_staff.csv", sample_data.staff_df().to_csv(index=False), "sample_staff.csv", "text/csv")

# ------------------------------------------------------------------ landing page
if not S.data:
    st.markdown('<div class="hero"><h1>Analytics Studio</h1><p>Upload any Excel or CSV file and get a colourful, '
                'interactive report in seconds. No formulas, no setup.</p></div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    a.markdown('<div class="step"><b>1. Upload</b><br>Drop an Excel or CSV file in the sidebar, or click a sample.</div>', unsafe_allow_html=True)
    b.markdown('<div class="step"><b>2. Choose</b><br>Pick what to measure, how to group it, and a date column. Add filters and a target.</div>', unsafe_allow_html=True)
    c.markdown('<div class="step"><b>3. Read and export</b><br>See KPIs, insights, forecast and charts. Download an Excel report.</div>', unsafe_allow_html=True)
    st.caption("Your data stays in your own browser session and is not shared with other visitors.")
    st.stop()

# ------------------------------------------------------------------ sidebar (analysis controls)
with st.sidebar:
    ids = list(S.data)
    idx = ids.index(S.ds) if S.get("ds") in ids else len(ids) - 1
    ds = st.selectbox("Dataset", ids, index=idx, format_func=lambda i: f"{S.data[i]['name']} (#{i})")
    S.ds = ds
    D = S.data[ds]
    df, types = D["df"], D["types"]
    cols = an.describe_columns(df, types)
    nums = [c["name"] for c in cols if c["type"] == "num"]
    cats = [c["name"] for c in cols if c["type"] == "cat" and c["unique"] > 1]
    dates = [c["name"] for c in cols if c["type"] == "date"]

    st.markdown("### 2. Analyze")
    if S.get("pending_measure"):
        S[f"m{ds}"] = S.pop("pending_measure")
    measure = sel("Measure (number)", nums, f"m{ds}", pick(nums, "revenue|sales|amount|total|profit|salary|value|price|cost")) if nums else None
    agg = sel("Calculate", list(AGG), f"a{ds}", format_func=AGG.get) if measure else "count"
    group = sel("Group by", cats, f"g{ds}", pick(cats, "product|category|department|region|name|type")) if cats else None
    split = sel("Split by", cats, f"s{ds}", next((c for c in cats if c != group), group)) if cats else None
    date_col = sel("Date column", ["None"] + dates, f"d{ds}", dates[0] if dates else "None")
    date_col = None if date_col == "None" else date_col
    grain = sel("Time step", ["month", "year", "day"], f"t{ds}")
    fc = st.slider("Forecast steps", 0, 12, 3, key=f"fc{ds}")
    target = st.number_input("Target per time step (0 = off)", min_value=0.0, value=0.0, step=1000.0, key=f"tg{ds}")
    kind = st.radio("Trend chart", ["Bars", "Line", "Area"], horizontal=True)
    miss = st.selectbox("Empty numbers", list(MISSING), format_func=MISSING.get, key=f"ms{ds}")

    st.markdown("### 3. Duplicates")
    DMODE = {"exact": "Exact copies (all columns match)", "keys": "Chosen columns match", "none": "Don't remove any"}
    dmode = st.radio("Remove duplicate rows by", list(DMODE), format_func=DMODE.get, key=f"dm{ds}")
    dkeys, dkeep = None, "first"
    if dmode == "keys":
        guess = [c for c in df.columns if types[c] == "id"][:1] + [c for c in df.columns if re.search("product|item|sku", c, re.I)][:1]
        dkeys = st.multiselect("Columns that identify one row", list(df.columns), default=guess or list(df.columns)[:1], key=f"dk{ds}")
        dkeep = st.radio("Keep the", ["first", "last"], horizontal=True, key=f"dp{ds}")
    base, removed = an.dedupe(df, dmode, dkeys, dkeep)
    st.caption(f"{removed:,} duplicate row(s) removed by this setting.")
    idc = [c for c in df.columns if types[c] == "id"][:1]
    if dmode == "exact" and idc:
        shared = int(base[idc[0]].duplicated(keep=False).sum())
        if shared:
            st.caption(f"⚠ {shared:,} rows share a {idc[0]} with another row but differ in other columns. "
                       f"This is normal if one {idc[0]} has several lines. If not, choose 'Chosen columns'.")

    st.markdown("### 4. Filters")
    filters, date_from, date_to = {}, None, None
    for c in [c for c in cols if c["type"] == "cat" and c.get("values")][:5]:
        chosen = st.multiselect(c["name"], c["values"], key=f"f{ds}{c['name']}")
        if chosen:
            filters[c["name"]] = chosen
    if date_col:
        months = next(c["months"] for c in cols if c["name"] == date_col)
        if len(months) > 1:
            date_from, date_to = st.select_slider("Date range", months, value=(months[0], months[-1]), key=f"r{ds}{date_col}")

    if len(nums) > 1:
        with st.expander("➕ Add a calculated column"):
            with st.form("calc", clear_on_submit=True):
                ca, cb = st.selectbox("Column A", nums), st.selectbox("Column B", nums, index=1)
                op = st.selectbox("Operation", ["*", "-", "+", "/"])
                nm = st.text_input("New column name", placeholder="e.g. Profit")
                if st.form_submit_button("Add column"):
                    try:
                        D["df"], D["types"] = an.add_calc_column(df, types, ca, op, cb, nm)
                        S.pending_measure = nm.strip()
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
    if st.button("🗑 Remove this dataset"):
        del S.data[ds]
        S.pop("ds", None)
        st.rerun()

# ------------------------------------------------------------------ analysis
work = an.fill_missing(base, types, miss)
view = an.apply_filters(work, filters, date_col, date_from, date_to)
params = {"measure": measure, "agg": agg, "group_by": group, "split_by": split, "date_col": date_col, "grain": grain,
          "target": target, "forecast": fc, "date_from": date_from, "date_to": date_to, "filters": filters}
res = an.summarize(work, types, params)
k, t = res["kpis"], res["trend"]


def style(fig, h=340):
    fig.update_layout(template="plotly_dark", height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      colorway=P, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=1.12))
    fig.update_xaxes(gridcolor="#ffffff14")
    fig.update_yaxes(gridcolor="#ffffff14")
    return fig


def kpi(col, i, label, value):
    bg = f"linear-gradient(135deg,{P[i % len(P)]},{P[(i + 2) % len(P)]})"
    col.markdown(f'<div class="kpi" style="background:linear-gradient(#0000002e,#0000002e),{bg}"><span>{label}</span><b>{value}</b></div>',
                 unsafe_allow_html=True)


st.markdown(f'<div class="hero"><h1>{D["name"]}</h1><p>{len(df):,} rows · {len(cols)} columns · '
            f'{len(nums)} numbers · {len(dates)} dates · {len(cats)} categories</p></div>', unsafe_allow_html=True)

if S.get("report") and S.get("ds") == ds:
    r = D["report"]
    with st.expander("🧹 Cleaning report for this file"):
        a, b, c, d = st.columns(4)
        a.metric("Rows read", r["rows_read"])
        b.metric("Empty rows removed", r["empty_removed"])
        c.metric("Exact duplicates found", r.get("duplicates_found", r["duplicates_removed"]))
        d.metric("Rows loaded", r["rows_loaded"])

cards = [("Records", nf(k["records"]))]
if measure:
    cards += [(f"Total {measure}", nf(k["total"])), (f"Average {measure}", nf(k["average"])), (f"Highest {measure}", nf(k["highest"]))]
if k["change_pct"] is not None:
    cards.append((f"Last {grain} vs previous", f"{k['change_pct']:+.1f}%"))
if target and t["periods"]:
    cards.append((f"Target met ({nf(target)})", f"{t['met']} of {len(t['periods'])}"))
for i, (col, (lab, val)) in enumerate(zip(st.columns(len(cards)), cards)):
    kpi(col, i, lab, val)

st.markdown("#### 💡 Key insights")
for i, s in enumerate(res["insights"]):
    st.markdown(f'<div class="ins" style="border-left:5px solid {P[i % len(P)]}">{re.sub(r"[*][*](.+?)[*][*]", r"<b>\1</b>", s)}</div>',
                unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Overview", "🔗 Relationships", "🧮 Pivot table", "🗂 Data", "📥 Export"])

with tab1:
    st.markdown(f"**{res['label']} by {grain}**" + (" with forecast" if t["forecast_periods"] else ""))
    if t["periods"]:
        per, val = t["periods"], t["values"]
        fig = go.Figure()
        if kind == "Bars":
            fig.add_bar(x=per, y=val, name=res["label"], marker_color=[P[0] if not target or v >= target else "#EF4444" for v in val])
        elif kind == "Line":
            fig.add_scatter(x=per, y=val, name=res["label"], mode="lines+markers", line=dict(color=P[0], width=3))
        else:
            fig.add_scatter(x=per, y=val, name=res["label"], mode="lines", fill="tozeroy", line=dict(color=P[0], width=3))
        if t["forecast_periods"]:
            fig.add_scatter(x=[per[-1]] + t["forecast_periods"], y=[val[-1]] + t["forecast_values"], name="Forecast",
                            mode="lines+markers", line=dict(color=P[3], dash="dash", width=3))
        if target:
            fig.add_hline(y=target, line_dash="dot", line_color="#EF4444", annotation_text="Target")
        st.plotly_chart(style(fig))
    else:
        st.info("Pick a date column in the sidebar to see a trend over time.")
    left, right = st.columns(2)
    with left:
        st.markdown(f"**Top {group}: {res['label']}**" if group else "**Top groups**")
        if res["groups"]:
            g = res["groups"][::-1]
            st.plotly_chart(style(go.Figure(go.Bar(x=[x["value"] for x in g], y=[x["name"] for x in g], orientation="h",
                                                   marker=dict(color=[x["value"] for x in g], colorscale=[[0, P[1]], [1, P[0]]])))))
    with right:
        st.markdown(f"**Share by {split}**" if split else "**Share**")
        if res["split"]:
            st.plotly_chart(style(go.Figure(go.Pie(labels=[x["name"] for x in res["split"]], values=[max(0, x["value"]) for x in res["split"]],
                                                   hole=0.55, marker=dict(colors=P, line=dict(color="#0B1020", width=2))))))
    h = res["histogram"]
    if h["counts"]:
        st.markdown(f"**How {measure} is spread across records**")
        mid = [nf((a + b) / 2) for a, b in zip(h["edges"][:-1], h["edges"][1:])]
        st.plotly_chart(style(go.Figure(go.Bar(x=mid, y=h["counts"], marker=dict(color=h["counts"], colorscale=[[0, P[2]], [1, P[3]]]))), 280))

with tab2:
    if len(nums) < 2:
        st.info("This file needs at least two numeric columns to compare.")
    else:
        cx, cy = st.columns(2)
        x = cx.selectbox("X axis", nums, key=f"rx{ds}")
        y = cy.selectbox("Y axis", nums, index=1, key=f"ry{ds}")
        rel = an.relationship(view, types, x, y)
        if rel["points"]:
            xs, ys = zip(*rel["points"])
            fig = go.Figure(go.Scatter(x=xs, y=ys, mode="markers", name="Records",
                                       marker=dict(size=8, opacity=.75, color=ys, colorscale=[[0, P[1]], [1, P[2]]])))
            vx = sum((a - sum(xs) / len(xs)) ** 2 for a in xs)
            if vx:
                slope = sum((a - sum(xs) / len(xs)) * (b - sum(ys) / len(ys)) for a, b in zip(xs, ys)) / vx
                icpt = sum(ys) / len(ys) - slope * sum(xs) / len(xs)
                fig.add_scatter(x=[min(xs), max(xs)], y=[slope * min(xs) + icpt, slope * max(xs) + icpt], mode="lines",
                                line=dict(color=P[3], width=3, dash="dash"), name="Trend line")
            fig.update_xaxes(title=x)
            fig.update_yaxes(title=y)
            st.plotly_chart(style(fig, 380))
            if rel["r"] is not None:
                r_ = rel["r"]
                word = "strong" if abs(r_) >= .7 else "moderate" if abs(r_) >= .4 else "weak"
                st.markdown(f"**Correlation r = {r_:.2f}** ({word} {'positive' if r_ >= 0 else 'negative'})")
        cm = rel["correlations"]
        if cm["matrix"]:
            st.markdown("**Correlation heat map**")
            st.plotly_chart(style(go.Figure(go.Heatmap(
                z=cm["matrix"], x=cm["columns"], y=cm["columns"], zmin=-1, zmax=1, colorscale=[[0, P[2]], [.5, "#1E2442"], [1, P[0]]],
                text=[[f"{v:.2f}" if v is not None else "" for v in row] for row in cm["matrix"]], texttemplate="%{text}")), 380))

with tab3:
    if not cats:
        st.info("This file has no category columns for a pivot table.")
    else:
        pa, pb = st.columns(2)
        prow = pa.selectbox("Rows", cats, key=f"pr{ds}")
        pcol = pb.selectbox("Columns", ["None"] + [c for c in cats if c != prow], key=f"pc{ds}")
        pv = an.pivot(view, prow, None if pcol == "None" else pcol, measure, agg)
        st.caption(f"{res['label']} · filters from the sidebar apply")
        st.dataframe(pv)
        body = pv.drop(index="Total", errors="ignore").drop(columns="Total", errors="ignore")
        if pcol != "None" and body.shape[0] > 1 and body.shape[1] > 1:
            st.plotly_chart(style(go.Figure(go.Heatmap(z=body.values, x=[str(c) for c in body.columns], y=[str(i) for i in body.index],
                                                       colorscale=[[0, "#1E2442"], [1, P[0]]])), 360))

with tab4:
    show = view.head(500).copy()
    for c in show.select_dtypes("datetime").columns:
        show[c] = show[c].dt.strftime("%Y-%m-%d")
    st.caption(f"Showing {len(show):,} of {len(view):,} rows")
    st.dataframe(show, height=360)
    st.markdown("**Columns found**")
    prof = [{"column": c["name"], "detected as": {"num": "Number", "date": "Date", "cat": "Category", "id": "Identifier"}[c["type"]],
             "unique values": c["unique"], "missing": c["missing"], "missing %": round(c["missing"] / max(1, len(df)) * 100, 1)} for c in cols]
    st.dataframe(prof)

with tab5:
    st.caption("Exports use the current filters. Click Prepare again after you change a filter or setting.")
    sig = repr((ds, miss, {k_: v for k_, v in params.items()}))
    e1, e2 = st.columns(2)
    if e1.button("Prepare Excel report"):
        S.xlsx = (sig, an.report_xlsx(view, res))
    if S.get("xlsx") and S.xlsx[0] == sig:
        e1.download_button("⬇ Download Excel report", S.xlsx[1], "analytics-report.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if e2.button("Prepare cleaned CSV"):
        S.csv = (sig, view.to_csv(index=False).encode())
    if S.get("csv") and S.csv[0] == sig:
        e2.download_button("⬇ Download cleaned CSV", S.csv[1], "cleaned-data.csv", "text/csv")
