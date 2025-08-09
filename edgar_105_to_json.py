#!/usr/bin/env python3
"""
edgar_105_to_json.py
Fetch SEC 8-K filings referencing "Material Cybersecurity Incidents" / "Item 1.05" and write JSON.
Intended to be run by GitHub Actions, but can also be run locally.

Usage (local):
  python3 edgar_105_to_json.py --out public/sec-105.json --days 180
"""
import requests, json, re, argparse
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf

USER_AGENT = 'Eden Cyber (edencyber.com) via GitHub Actions'

def get_timestamp_from_index(index_href):
    headers = { 'User-Agent': USER_AGENT }
    r = requests.get(index_href, headers=headers, timeout=30)
    r.raise_for_status()
    match = re.findall('<div class="info">(.*?)</div>', r.text)
    if len(match) >= 2:
        return match[1]
    return None

def get_filings(start_date, end_date, max_results=999999):
    base_url = "https://efts.sec.gov/LATEST/search-index"
    results = []
    fetched = 0
    page_size = 100
    total_available = None

    while fetched < max_results:
        query = {
            'q':'"Material Cybersecurity Incidents" OR "Item 1.05"',
            'forms': '8-K',
            'startdt': start_date,
            'enddt': end_date,
            'from': str(fetched),
            'size': page_size,
            'sort': 'desc'
        }
        headers = {'User-Agent': USER_AGENT, 'Accept': 'application/json'}
        resp = requests.get(base_url, headers=headers, params=query, timeout=30)
        resp.raise_for_status()

        data = resp.json()
        filings = data['hits']['hits']
        if total_available is None:
            total_available = data['hits']['total']['value']
        if not filings:
            break

        for f in filings:
            src = f['_source']
            display_names = src.get('display_names', [])
            company_name = display_names[0] if display_names else 'N/A'
            ciks = src.get('ciks', [])
            cik = ciks[0] if ciks else 'N/A'
            filing_date = src.get('file_date', 'N/A')
            form_type = src.get('form', 'N/A')
            adsh = src.get('adsh', 'N/A')
            doc_id = f.get('_id', 'N/A').split(':')[1] if f.get('_id') else 'N/A'
            filing_href = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{adsh}-index.htm"
            document_href = f"https://www.sec.gov/Archives/edgar/data/{cik}/{adsh.replace('-', '')}/{doc_id}"

            # Derive ticker from display name if present
            import re as _re
            ticker = 'N/A'
            if display_names:
                m = _re.findall(r'\((.*?)\)', display_names[0])
                if m and not m[0].startswith("CIK "):
                    ticker = m[0].split(",")[0]

            published_timestamp = get_timestamp_from_index(filing_href)

            results.append({
                'company_name': company_name,
                'cik': cik,
                'filing_date': filing_date,
                'form_type': form_type,
                'filing_href': filing_href,
                'document_href': document_href,
                'ticker': ticker,
                'published_timestamp': published_timestamp
            })

        fetched += len(filings)
        if fetched >= total_available or len(filings) < page_size:
            break

    return results

def analyze_impact(ticker, filing_date):
    if ticker in (None, "", "N/A"):
        return None, None, None
    try:
        fd = pd.to_datetime(filing_date).normalize()
    except Exception:
        return None, None, None
    if fd.date() == datetime.utcnow().date():
        return None, None, None

    start_delta = 1
    end_delta = 1
    while (start_delta + end_delta) < 10:
        dr = pd.bdate_range(start=fd - pd.Timedelta(days=start_delta), end=fd + pd.Timedelta(days=end_delta)).normalize()
        try:
            df = yf.download(ticker, start=dr.min().strftime('%Y-%m-%d'), end=(dr.max() + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), progress=False)
        except Exception:
            return None, None, None
        if df.empty:
            start_delta += 1; end_delta += 1; continue
        if pd.Timestamp(dr.max().date()) not in df.index:
            start_delta += 1; end_delta += 1; continue
        try:
            before = float(df.loc[dr.min(), 'Close'])
            after = float(df.loc[dr.max(), 'Close'])
            pct = (after - before) / before * 100.0
            return before, after, pct
        except Exception:
            start_delta += 1; end_delta += 1; continue
    return None, None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="public/sec-105.json", help="Output JSON path (default public/sec-105.json)")
    ap.add_argument("--days", type=int, default=180, help="Look back N days (default 180)")
    args = ap.parse_args()

    end_date = datetime.utcnow().strftime('%Y-%m-%d')
    start_date = (datetime.utcnow() - timedelta(days=args.days)).strftime('%Y-%m-%d')

    filings = get_filings(start_date, end_date)
    enriched = []
    for f in filings:
        before, after, pct = analyze_impact(f.get('ticker'), (f.get('published_timestamp') or f.get('filing_date')).split(' ')[0])
        f['price_before'] = before
        f['price_after'] = after
        f['pct_change'] = pct
        enriched.append(f)

    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "start_date": start_date,
        "end_date": end_date,
        "count": len(enriched),
        "results": enriched
    }

    with open(args.out, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
    print(f"Wrote {len(enriched)} records to {args.out}")

if __name__ == "__main__":
    main()
