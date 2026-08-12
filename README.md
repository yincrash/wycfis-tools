# wycfis-tools

Open-source tools for pulling Wyoming campaign finance data out of
[WYCFIS](https://www.wycampaignfinance.gov), the Wyoming Secretary of State's
Campaign Finance Information System.

WYCFIS has no API and no bulk download. These scripts drive the public search
pages headlessly and turn the results into CSVs anyone can analyze.

## What you get

| Script | Output |
|---|---|
| `fetch_reports.py <year>` | Every filed report's summary PDF (candidate/committee identity, office sought, report totals) plus an index CSV |
| `reports_to_csv.py out/<year>` | One CSV row per filed report: filer, office, period, date filed, total contributions, total expenditures, carried-forward (cash on hand) |
| `fetch_exports.py contributions <year>` | WYCFIS's own itemized contributions export (every disclosed contribution: donor, recipient, type, date, amount) |
| `fetch_exports.py expenditures <year>` | Itemized expenditures export (payee, purpose, date, amount) |

## Setup

```bash
pip install requests beautifulsoup4 pdfplumber
```

## Usage

```bash
# 1. download all filed report summaries for the 2026 cycle (~15 min for ~300 reports)
python3 fetch_reports.py 2026

# 2. convert the PDFs into a single CSV
python3 reports_to_csv.py out/2026

# 3. itemized money, straight from WYCFIS's export buttons
python3 fetch_exports.py contributions 2026 -o out/2026/contributions.csv
python3 fetch_exports.py expenditures  2026 -o out/2026/expenditures.csv
```

`fetch_reports.py` is resumable: it appends to its index as each PDF lands, so
if it dies mid-run (WYCFIS can be flaky), rerun the same command and it picks
up where it left off. `reports_to_csv.py` parses each filer's identity from
the PDF itself, never from download order, so reports cannot be mis-attributed.

## Things to know about the data

- **"Election year cycle" includes the prior odd year.** Searching 2026 also
  returns 2025 annual reports.
- **Exports only show disclosed money.** Contribution/expenditure records
  appear only when FILED (attached to a submitted report) or PUBLISHED
  (voluntarily disclosed early). A campaign that has not filed shows nothing,
  which is not the same as having nothing.
- **Reports have summary totals; exports have itemized records.** The report
  PDF totals (from `reports_to_csv.py`) are the authoritative per-report
  numbers, including un-itemized small contributions and cash on hand.
- **Committee names are not candidate names.** Expect "FRIENDS OF ...",
  old committees reused for new races, and both "LAST, FIRST" and
  "FIRST LAST" account spellings for the same person. Joining accounts to
  candidates takes care; the official candidate roster on
  [sos.wyo.gov](https://sos.wyo.gov/Elections/) is the best join target.
- Statewide and legislative filings only; county-office reports are filed
  with county clerks and mostly absent from WYCFIS.

## Legal notice

Wyoming Statute 22-2-113(c): "Information copied from campaign receipt and
expenditure reports filed by state and local candidates may be used for
political purposes but shall not be used for commercial purposes." Violators
may be punished by law. Use this data accordingly.

The scripts rate-limit themselves (one request every ~0.4 s). Please keep it
that way; WYCFIS is a small state system.

## License

MIT
