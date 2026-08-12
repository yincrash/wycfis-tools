#!/usr/bin/env python3
"""Shared plumbing for scraping WYCFIS (wycampaignfinance.gov).

WYCFIS is an ASP.NET WebForms app: every interaction is a POST of the full
form state (viewstate + all field defaults) with __EVENTTARGET naming the
control that "clicked". These helpers hide that dance.
"""
import re
import time

import requests
from bs4 import BeautifulSoup

BASE = "https://www.wycampaignfinance.gov/WYCFWebApplication"
SEARCH_FILING_URL = f"{BASE}/GSF_SystemConfiguration/SearchFilingPublic.aspx"
FILING_VIEWER_URL = f"{BASE}/Reports/FilingSummaryViewer.aspx"
CONTRIBUTIONS_URL = f"{BASE}/GSF_SystemConfiguration/SearchContributions.aspx"
EXPENDITURES_URL = f"{BASE}/GSF_SystemConfiguration/SearchExpenditures.aspx"

USER_AGENT = "wycfis-tools/1.0 (open-source public records tool)"
POLITE_DELAY_SECONDS = 0.4


def new_session():
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def soup_of(response):
    return BeautifulSoup(response.text, "html.parser")


def form_data(soup):
    """Hidden fields plus defaults for every visible control, ready to POST."""
    data = {}
    for inp in soup.select("input"):
        name = inp.get("name")
        if not name:
            continue
        itype = (inp.get("type") or "text").lower()
        if itype in ("hidden", "text", "password"):
            data[name] = inp.get("value", "")
        elif itype in ("checkbox", "radio") and inp.has_attr("checked"):
            data[name] = inp.get("value", "on")
    for sel in soup.select("select"):
        name = sel.get("name")
        if not name:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        if opt is not None:
            data[name] = opt.get("value", "")
    return data


def postback(session, url, soup, target, argument="", extra=None, timeout=120):
    """POST the page's form state with __EVENTTARGET=target."""
    data = form_data(soup)
    data["__EVENTTARGET"] = target
    data["__EVENTARGUMENT"] = argument
    # a doPostBack must not also carry submit-button fields
    for k in list(data):
        if k.endswith(("$btnSearch", "$btnClear", "$bntSearch", "$btnExport")):
            del data[k]
    if extra:
        data.update(extra)
    time.sleep(POLITE_DELAY_SECONDS)
    r = session.post(url, data=data, timeout=timeout)
    r.raise_for_status()
    return r


def submit(session, url, soup, button, extra=None, timeout=300):
    """POST the form as if `button` (name attr) was clicked."""
    data = form_data(soup)
    data["__EVENTTARGET"] = ""
    data["__EVENTARGUMENT"] = ""
    data[button] = "Search" if "earch" in button else "Export"
    if extra:
        data.update(extra)
    time.sleep(POLITE_DELAY_SECONDS)
    r = session.post(url, data=data, timeout=timeout)
    r.raise_for_status()
    return r


def slugify(text, max_len=80):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()[:max_len]
