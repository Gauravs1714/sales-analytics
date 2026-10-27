# Analytics Studio - End-to-End Sales Analytics and Reporting System

Upload **any** Excel or CSV file. The app cleans it, detects which columns are numbers, dates and
categories, and builds an interactive, colourful dashboard from whatever columns the file has.
Change a column choice and every chart, KPI and insight updates.

```
Excel / CSV -> Pandas cleaning + type detection -> KPIs, forecast, insights -> Streamlit + Plotly dashboard -> Excel report
```

## Features
- Works with any columns (types detected automatically: number, date, category, identifier)
- Cleaning report: rows read, empty rows removed, duplicates removed
- Choose how to treat empty numbers: leave, fill with 0, fill with average, remove rows
- KPIs, auto insights, trend with forecast, target alerts, top groups, share, distribution
- Excel-style pivot table with totals and a heat map
- Relationship explorer (scatter + trend line) and correlation heat map
- Calculated columns (for example Quantity x Unit Price = Revenue)
- Filters for every category column plus a date range
- Four colour themes; bar, line or area trend
- Excel report (Summary, By group, Trend, Data) and cleaned CSV export
- Optional REST API (FastAPI) in `api/main.py`

## Run on your computer
```bash
python -m venv venv
venv\Scripts\activate            # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
streamlit run dashboard/app.py   # opens http://localhost:8501
```
Click **Sales sample** or **Staff sample**, or upload your own file.

## Deploy free
Follow **DEPLOY.md** (GitHub + Streamlit Community Cloud, about 15 minutes).

## Optional: REST API
```bash
pip install -r requirements-api.txt
uvicorn api.main:app --reload    # docs at http://localhost:8000/docs
```
The API stores uploads in a local `storage/` folder. The hosted dashboard does not need it.

## Project structure
```
dashboard/app.py          Streamlit dashboard (the app you deploy)
dashboard/sample_data.py  sample sales and staff data
api/analytics.py          cleaning, type detection, KPIs, forecast, insights, pivot, Excel report
api/main.py               optional FastAPI endpoints
api/db.py                 optional file storage for the API
.streamlit/config.toml    dark theme
requirements.txt          packages for the dashboard
requirements-api.txt      extra packages for the optional API
```

## Tech
Python, Pandas, NumPy, Streamlit, Plotly, openpyxl, FastAPI (optional)
