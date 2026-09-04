"""twister_api.py - fetch Amazon PDP twister dimension-slot AJAX (variation/pricing fragment)."""

import json
import re
import sys
from urllib.parse import urlencode

from amazon import fetch, fetch_ajax, log, asin_from_input, _is_captcha_ajax
from product import rip_product


def _bad_twister_response(html):
    return not html or _is_captcha_ajax(html)


def _extract_embedded_twister_url(html):
    for pat in (
        r'(https://www\.amazon\.com/gp/product/ajax/twisterDimensionSlotsDefault[^"\'\s<>]+)',
        r'"(/gp/product/ajax/twisterDimensionSlotsDefault[^"\'\\]+)"',
        r"'(/gp/product/ajax/twisterDimensionSlotsDefault[^'\"\\]+)'",
    ):
        m = re.search(pat, html)
        if not m:
            continue
        u = m.group(1).replace("\\u0026", "&").replace("&amp;", "&")
        if u.startswith("/"):
            u = "https://www.amazon.com" + u.split("\\")[0]
        return u
    return None


def _child_asins(html):
    ids = []
    seen = set()
    asin_map_m = re.search(r'"dimensionValuesDisplayData"\s*:\s*\{(.*?)\}\s*[,}]', html, re.DOTALL)
    if asin_map_m:
        for m in re.finditer(r'"([A-Z0-9]{10})"\s*:\s*\[', asin_map_m.group(1)):
            a = m.group(1)
            if a not in seen:
                seen.add(a)
                ids.append(a)
    if not ids:
        for m in re.finditer(r'"asin_to_asin_map"\s*:\s*\{([^}]{20,500})\}', html, re.DOTALL):
            for sub in re.finditer(r'"([A-Z0-9]{10})"\s*:\s*"([A-Z0-9]{10})"', m.group(1)):
                for a in (sub.group(1), sub.group(2)):
                    if a not in seen:
                        seen.add(a)
                        ids.append(a)
    return ids


def _first_str(html, key):
    m = re.search(r'"' + re.escape(key) + r'"\s*:\s*"([^"]*)"', html)
    return m.group(1) if m else None


def build_twister_url(html, landing_asin, dp_url):
    emb = _extract_embedded_twister_url(html)
    if emb:
        return emb

    parent = _first_str(html, "parentAsin") or rip_product(html, dp_url).get("parent_asin") or landing_asin
    kids = _child_asins(html)
    if landing_asin not in kids:
        kids.insert(0, landing_asin)
    asin_list = ",".join(dict.fromkeys(kids))

    ptd = _first_str(html, "productTypeDefinition") or "UNKNOWN"
    pgid = _first_str(html, "productGroupId") or "pc_display_on_website"
    tw_flavor = _first_str(html, "twisterFlavor") or "twisterPlusDesktopConfigurator"

    q = {
        "isDimensionSlotsAjax": "1",
        "asinList": asin_list,
        "vs": "1",
        "asin": landing_asin,
        "productTypeDefinition": ptd,
        "productGroupId": pgid,
        "parentAsin": parent,
        "isPrime": "0",
        "deviceOs": "unrecognized",
        "landingAsin": landing_asin,
        "deviceType": "web",
        "showFancyPrice": "false",
        "twisterFlavor": tw_flavor,
    }
    return "https://www.amazon.com/gp/product/ajax/twisterDimensionSlotsDefault?" + urlencode(q)


def cmd_twister(args):
    asin, dp_url = asin_from_input(args.target)
    if not asin:
        log("x", f"can't parse ASIN from: {args.target}")
        sys.exit(1)
    log("~", f"PDP fetch {dp_url}")
    html = fetch(dp_url)
    if not html:
        sys.exit(1)
    tw_url = build_twister_url(html, asin, dp_url)
    log("~", f"twister GET …{tw_url[-80:]}")

    frag = fetch_ajax(tw_url, referer=dp_url)
    if _bad_twister_response(frag):
        log("~", "retry twister with navigation headers + lax captcha check")
        frag = fetch(tw_url, referer=dp_url, lax_captcha=True)

    if not frag or _bad_twister_response(frag):
        log("x", "twister blocked or empty - refresh frozen-profile.json from a fresh browser HAR")
        sys.exit(1)

    if args.format == "json":
        out = json.dumps({"twister_url": tw_url, "referer": dp_url, "fragment_html": frag}, indent=2, ensure_ascii=False)
    else:
        out = frag

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        log("+", f"written to {args.output}")
    else:
        print(out)
