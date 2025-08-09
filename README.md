# SEC 8-K Item 1.05 Feed (GitHub Actions + Pages)

This repo generates a JSON feed of recent 8-K filings mentioning **"Material Cybersecurity Incidents" (Item 1.05)** and publishes it to **GitHub Pages**.

## How it works
- **GitHub Actions** runs daily (cron) or manual dispatch.
- It executes `edgar_105_to_json.py`.
- Output is written to `public/sec-105.json` and deployed to Pages along with `public/index.html`.

## Quick start
1. Create a new GitHub repo, then upload these files.
2. In repo settings, enable **Pages** with **Source: GitHub Actions**.
3. Go to **Actions** and run **Build & Deploy SEC 1.05 Feed** (or wait for the daily cron).
4. Your feed will be at: `https://<your-username>.github.io/<repo-name>/sec-105.json`
   (Viewer page: `.../index.html`)

## WordPress integration
Install the `edencyber-sec-105` plugin and add a page with:
```
[sec_105_feed src="https://<your-username>.github.io/<repo-name>/sec-105.json" limit="100"]
```
This renders the live table on your site.

## Local dev
```
pip install -r requirements.txt
python edgar_105_to_json.py --out public/sec-105.json --days 180
```
Then open `public/index.html` in a browser.
