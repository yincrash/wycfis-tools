#!/usr/bin/env python3
"""Convert WYCFIS filing-summary PDFs (from fetch_reports.py) into one CSV.

Every field is parsed from the PDF itself - filer identity, office sought,
reporting period, and the report totals - so the output cannot mis-attribute
a report even if the download index is stale.

Usage:
  python3 reports_to_csv.py out/2026                 # reads out/2026/report_pdfs
  python3 reports_to_csv.py out/2026 -o filings.csv
"""
import argparse
import csv
import glob
import os
import re

import pdfplumber

MONEY_RE = re.compile(r"\(?\$([\d,]*\.?\d*)\)?")

LABELS = {
    "Reporting Period:": "reporting_period",
    "Date Filed:": "date_filed",
    "Account Type:": "account_type",
    "Account Name:": "account_name",
    "Candidate Name:": "candidate_name",
    "Committee Name:": "committee_name",
    "Office Sought:": "office_sought",
    "Total Carried Forward from Last Report:": "carried_forward_last",
    "Total of all Contributions:": "total_contributions",
    "Total Expenditures:": "total_expenditures",
    "Report Total:": "report_total",
    "Total Amended Contributions:": "amended_contributions",
    "Total Amended Expenditure:": "amended_expenditures",
    "Amendment Total:": "amendment_total",
    "Total Carried Forward:": "total_carried_forward",
}
MONEY_FIELDS = {v for v in LABELS.values()
                if v.startswith(("carried", "total", "report", "amend"))}

FIELDS = ["pdf_file", "account_name", "candidate_name", "committee_name",
          "account_type", "office_sought", "reporting_period", "date_filed",
          "carried_forward_last", "total_contributions", "total_expenditures",
          "report_total", "amended_contributions", "amended_expenditures",
          "amendment_total", "total_carried_forward"]


def parse_money(s):
    neg = "(" in s
    m = MONEY_RE.search(s)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    val = 0.0 if raw in ("", ".") else float(raw)
    return -val if neg else val


TITLE_RE = re.compile(
    r"^(Primary|General|Non ?-?Election|Annual|Special)[\w ()-]*\d{4}$", re.I)


def parse_pdf(path):
    out = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:2]:
            for line in page.extract_text_lines():
                text = line["text"].strip()
                for label, field in LABELS.items():
                    if text.startswith(label) and field not in out:
                        val = text[len(label):].strip()
                        out[field] = parse_money(val) if field in MONEY_FIELDS else val
                # "Reporting Period:" sometimes wraps with an empty value;
                # the report's title line carries the same information
                if not out.get("reporting_period") and TITLE_RE.match(text):
                    out["reporting_period"] = text.upper()
            if "total_carried_forward" in out:
                break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", help="output directory used by fetch_reports.py (e.g. out/2026)")
    ap.add_argument("-o", "--output", default=None,
                    help="CSV path (default <directory>/filings.csv)")
    args = ap.parse_args()

    pdf_dir = os.path.join(args.directory, "report_pdfs")
    out_path = args.output or os.path.join(args.directory, "filings.csv")
    pdfs = sorted(glob.glob(os.path.join(pdf_dir, "*.pdf")))
    if not pdfs:
        raise SystemExit(f"no PDFs found in {pdf_dir} - run fetch_reports.py first")

    n_ok, n_err = 0, 0
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for path in pdfs:
            try:
                rec = parse_pdf(path)
            except Exception as e:
                print(f"  !! failed to parse {os.path.basename(path)}: {e}")
                n_err += 1
                continue
            rec["pdf_file"] = os.path.basename(path)
            if not (rec.get("account_name") or rec.get("candidate_name")):
                print(f"  !! no filer identity found in {os.path.basename(path)} - check manually")
                n_err += 1
                continue
            w.writerow({k: ("" if rec.get(k) is None else rec.get(k, "")) for k in FIELDS})
            n_ok += 1
    print(f"wrote {n_ok} filings to {out_path} ({n_err} problems)")


if __name__ == "__main__":
    main()
