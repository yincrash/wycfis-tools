#!/usr/bin/env python3
"""Download every filed campaign-finance report summary PDF from WYCFIS.

Walks the "Search Filed Reports" grid for an election-year cycle, selects each
row, and saves that filing's summary PDF (an ActiveReports document containing
the filer's identity, office sought, and report totals).

Files are named from the row's content (account slug + period + row ordinal),
and the index CSV is appended row-by-row as PDFs land, so an interrupted run
leaves a consistent index. Re-running skips files already in the index.

Usage:
  python3 fetch_reports.py 2026                    # candidates (default tab)
  python3 fetch_reports.py 2026 --tab pacs         # PACs, organizations, parties
  python3 fetch_reports.py 2026 --out out/2026/x   # choose output directory
  python3 fetch_reports.py 2026 --max-pages 1      # smoke test: first page only
"""
import argparse
import csv
import os

import wycfis

# tab -> (menu index on the Search Filed Reports page, election-year field name)
TABS = {
    "candidates": (None, "ctl00$BodyContent$txtElectionYear"),
    "pacs": ("1", "ctl00$BodyContent$txtElectionYearPAC"),
    "organizations": ("2", "ctl00$BodyContent$txtElectionYearORG"),
    "parties": ("3", "ctl00$BodyContent$txtElectionYearPC"),
}


def grid_rows(soup):
    grid = soup.find(id="ctl00_BodyContent_gvFilingSearchResult")
    rows = []
    if grid is None:
        return rows
    for tr in grid.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != 5:
            continue
        texts = [" ".join(c.get_text(" ", strip=True).split()) for c in cells]
        if texts[0] == "Account Name":
            continue
        rows.append(texts[:4])
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("year", help="election year cycle, e.g. 2026 (covers the prior odd year too)")
    ap.add_argument("--tab", default="candidates", choices=sorted(TABS),
                    help="which filer type to download (default candidates)")
    ap.add_argument("--out", default=None, help="output directory (default out/<year>/<tab>)")
    ap.add_argument("--max-pages", type=int, default=None, help="stop after N grid pages (testing)")
    args = ap.parse_args()

    outdir = args.out or os.path.join("out", str(args.year), args.tab)
    tab_index, year_field = TABS[args.tab]
    pdf_dir = os.path.join(outdir, "report_pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    index_path = os.path.join(outdir, "report_index.csv")

    done = set()
    if os.path.exists(index_path):
        with open(index_path, newline="") as f:
            for row in csv.DictReader(f):
                done.add((row["account_name"], row["reporting_period"],
                          row["filing_type"], row["row_ordinal"]))
        print(f"resuming: {len(done)} filings already indexed")
    index_exists = os.path.exists(index_path)
    index_f = open(index_path, "a", newline="")
    index = csv.writer(index_f)
    if not index_exists:
        index.writerow(["account_name", "account_type", "filing_type",
                        "reporting_period", "row_ordinal", "pdf_file"])

    s = wycfis.new_session()
    r = s.get(wycfis.SEARCH_FILING_URL, timeout=60)
    soup = wycfis.soup_of(r)
    if tab_index is not None:
        r = wycfis.postback(s, wycfis.SEARCH_FILING_URL, soup,
                            "ctl00$BodyContent$mnuFilingReports", tab_index)
        soup = wycfis.soup_of(r)
    r = wycfis.submit(s, wycfis.SEARCH_FILING_URL, soup,
                      "ctl00$BodyContent$btnSearch",
                      extra={year_field: str(args.year)})
    soup = wycfis.soup_of(r)

    page, fetched, seen_first = 1, 0, None
    seen_keys = {}
    while True:
        rows = grid_rows(soup)
        if not rows or rows[0] == seen_first:
            break
        seen_first = rows[0]
        for i, row in enumerate(rows):
            # ordinal disambiguates identical (account, period, type) rows (amendments)
            base_key = (row[0], row[3], row[2])
            ordinal = seen_keys[base_key] = seen_keys.get(base_key, 0) + 1
            key = (row[0], row[3], row[2], str(ordinal))
            if key in done:
                continue
            fname = f"{wycfis.slugify(row[0])}__{wycfis.slugify(row[3])}__{wycfis.slugify(row[2])}_{ordinal}.pdf"
            r2 = wycfis.postback(s, wycfis.SEARCH_FILING_URL, soup,
                                 "ctl00$BodyContent$gvFilingSearchResult", f"select${i}",
                                 extra={year_field: str(args.year)})
            rv = s.get(wycfis.FILING_VIEWER_URL, timeout=180)
            if not rv.headers.get("Content-Type", "").lower().startswith("application/pdf"):
                print(f"  !! non-pdf response for {row[0]} ({row[3]}) - skipped")
                soup = wycfis.soup_of(r2)
                continue
            with open(os.path.join(pdf_dir, fname), "wb") as f:
                f.write(rv.content)
            index.writerow([row[0], row[1], row[2], row[3], ordinal, fname])
            index_f.flush()
            fetched += 1
            print(f"page {page} row {i}: {row[0]} | {row[3]} | {row[2]}")
            soup = wycfis.soup_of(r2)
        if args.max_pages and page >= args.max_pages:
            print(f"stopping at --max-pages {args.max_pages}")
            break
        page += 1
        r = wycfis.postback(s, wycfis.SEARCH_FILING_URL, soup,
                            "ctl00$BodyContent$gvFilingSearchResult", f"Page${page}",
                            extra={year_field: str(args.year)})
        soup = wycfis.soup_of(r)

    index_f.close()
    print(f"done: {fetched} new PDFs in {pdf_dir}; index at {index_path}")


if __name__ == "__main__":
    main()
