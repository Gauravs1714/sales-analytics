# Deploy Analytics Studio free (GitHub + Streamlit Community Cloud)

Time needed: about 15 minutes. Cost: free. No credit card.

## Part 0 - What you need
- A computer with Python 3.10 or newer (python.org/downloads; on Windows tick "Add Python to PATH")
- Git (git-scm.com/downloads)
- A free GitHub account (github.com)
- This project folder, unzipped

## Part 1 - Test it on your computer first
Open a terminal in the project folder (the folder that contains `dashboard`, `api` and `requirements.txt`).
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```
(Mac/Linux: use `source venv/bin/activate`.)
Your browser opens http://localhost:8501. Click **Sales sample**. If charts appear, it works.
If you see an error, fix it here before deploying. Press Ctrl+C in the terminal to stop.

## Part 2 - Put the code on GitHub
1. Tell Git who you are (once):
   ```
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
2. On github.com click **+** (top right) -> **New repository**.
   - Name: `sales-analytics`
   - Choose **Public** (Streamlit free hosting needs a public repo)
   - Do NOT tick "Add a README". Click **Create repository**.
3. In your terminal, in the project folder:
   ```
   git init
   git add .
   git commit -m "Analytics Studio"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/sales-analytics.git
   git push -u origin main
   ```
   A browser window may ask you to sign in to GitHub. Approve it.
4. Refresh the repo page. You must see `dashboard/`, `api/`, `requirements.txt` and `README.md`
   at the top level. If they are inside another folder, the deploy path in Part 3 will be wrong.

## Part 3 - Deploy on Streamlit Community Cloud
1. Go to **share.streamlit.io** and click **Continue with GitHub**. Authorize Streamlit.
2. Click **Create app** -> **Deploy a public app from GitHub**.
3. Fill in:
   - Repository: `YOUR_USERNAME/sales-analytics`
   - Branch: `main`
   - Main file path: `dashboard/app.py`
   - App URL: choose a name, for example `sales-analytics-gaurav`
4. Click **Advanced settings** and set Python version to **3.11** or **3.12**. No secrets are needed.
5. Click **Deploy**. Wait 2 to 5 minutes while it installs the packages.
6. Your app opens at `https://your-name.streamlit.app`. Click **Sales sample** to test it.

## Part 4 - Update the app later
Edit the code, then:
```
git add .
git commit -m "Describe your change"
git push
```
Streamlit redeploys automatically in about a minute. If it looks stuck, open the app menu
(bottom right, "Manage app") and choose **Reboot app**.

## Part 5 - Add it to your portfolio
- Project title: Analytics Studio - End-to-End Sales Analytics and Reporting System
- Buttons: **Live Demo** -> your streamlit.app link, **GitHub** -> your repo link
- Tech tags: Python, Pandas, NumPy, Streamlit, Plotly, Excel, FastAPI
- Add 2 or 3 screenshots (different colour themes) to the README
- Describe it honestly: "Upload any Excel/CSV; auto-cleans, detects column types, builds KPIs,
  insights, forecast and an Excel report."

## Common problems
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'api'` | Make sure `api/__init__.py` was pushed and `dashboard/app.py` is the main file path. |
| `ModuleNotFoundError` for another package | Add it to `requirements.txt`, push again. |
| App says it is asleep | Free apps sleep when nobody visits. Click the wake-up button and wait a minute. |
| Uploaded data disappears | By design. Data lives only in the visitor's session. Upload again. |
| Very large file is slow or crashes | Free hosting has limited memory. Try a file under about 50 MB. |
| Push rejected / asks for password | Use the browser sign-in, or GitHub Desktop (desktop.github.com). |

## Optional - Deploy the REST API too (Render, free)
New -> Web Service -> your repo. Build: `pip install -r requirements-api.txt`.
Start: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`. Open `/docs` on the link.
The free server sleeps when idle and loses saved files on restart, so treat it as a demo only.
