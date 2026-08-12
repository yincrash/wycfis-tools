#!/usr/bin/env python3
"""Download WYCFIS's own CSV exports of itemized contributions or expenditures.

These are the site's "Export" buttons on Search Contributions / Search
Expenditures, driven headlessly. Note: the exports contain only records that
are FILED (attached to a submitted report) or PUBLISHED (voluntarily disclosed
early) - money a campaign has received but not yet reported will not appear.

Usage:
  python3 fetch_exports.py contributions 2026 -o contributions_2026.csv
  python3 fetch_exports.py expenditures  2026 -o expenditures_2026.csv
"""
import argparse

import wycfis

PAGES = {
    "contributions": (wycfis.CONTRIBUTIONS_URL, "ctl00$BodyContent$bntSearch"),
    "expenditures": (wycfis.EXPENDITURES_URL, "ctl00$BodyContent$bntSearch"),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("kind", choices=sorted(PAGES))
    ap.add_argument("year", help="election year cycle, e.g. 2026")
    ap.add_argument("-o", "--output", required=True, help="output CSV path")
    args = ap.parse_args()

    url, search_btn = PAGES[args.kind]
    year_field = "ctl00$BodyContent$txtElectionYearCC"

    s = wycfis.new_session()
    r = s.get(url, timeout=60)
    soup = wycfis.soup_of(r)
    r = wycfis.submit(s, url, soup, search_btn, extra={year_field: str(args.year)})
    soup = wycfis.soup_of(r)
    marker = soup.find(string=lambda t: t and "Records" in t)
    print(f"search: {marker.strip() if marker else 'no result-count marker found'}")

    r = wycfis.submit(s, url, soup, "ctl00$BodyContent$btnExport",
                      extra={year_field: str(args.year)})
    ctype = r.headers.get("Content-Type", "")
    if "text" not in ctype.lower():
        raise SystemExit(f"unexpected export content-type: {ctype}")
    with open(args.output, "wb") as f:
        f.write(r.content)
    print(f"wrote {len(r.content):,} bytes to {args.output}")


if __name__ == "__main__":
    main()
