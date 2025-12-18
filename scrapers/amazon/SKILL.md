---
name: amazon
description: "Amazon product search + ASIN lookup via public endpoints. Trigger: /amazon, price comparison, product research, review scraping, deal hunt, ASIN lookup."
---

# /amazon

No-auth product intelligence. TLS-impersonated via `registry/frozen-profile.json`. All runtime data ships in `registry/`. No browser or local recon required for agents.

## Planes

```yaml
control: SKILL.md
data:
  frozen_profile: registry/frozen-profile.json   # browser fingerprint + headers
  urls:           registry/urls.json
  endpoints:      registry/endpoints.json
  selectors:      registry/selectors/*.json
execution:
  entry:          scripts/amazon.py
verify: tests/smoke.sh
```

## Subcommands

```yaml
rip:         { module: product.py,      args: "<ASIN|URL> [-f json|csv|table] [-o file]",                              desc: "extract product data" }
search:      { module: search.py,       args: "<query> [-n 10] [--min-rating 4.0] [-f json|table]",                    desc: "search products" }
reviews:     { module: reviews.py,      args: "<ASIN|URL> [-f json|table]",                                            desc: "inline reviews from product page" }
review-deep: { module: reviews.py,      args: "<ASIN|URL> [--pages 5] [--star five_star] [--verified] [--sort recent|helpful]", desc: "paginated review extraction with filters" }
category:    { module: search.py,       args: "<node_id|URL> [-n 20] [--sort price-asc|rating|newest] [--min-price N] [--max-price N] [--prime] [--min-rating 1-4]", desc: "browse category with filters" }
bestsellers: { module: feeds.py,        args: "[dept] [--feed best|new|movers|wished|gifted] [-n 20]",                 desc: "ranking feeds" }
deals:       { module: feeds.py,        args: "[-n 20]",                                                               desc: "active deals discovery" }
seller:      { module: seller.py,       args: "<seller_id> [-n 20]",                                                   desc: "seller profile + storefront products" }
variations:  { module: product.py,      args: "<ASIN|URL>",                                                            desc: "enumerate all child ASINs with dimension labels" }
harvest:     { module: amazon.py,       args: "<URL> [--pages N] [-o file]",                                           desc: "harvest ASINs from any page" }
batch:       { module: amazon.py,       args: "<file> [-f json|jsonl|csv|table] [-d 1.5]",                             desc: "batch rip from ASIN list" }
track:       { module: track.py,        args: "add <ASIN> [--label name] | check [--asin X] | history <ASIN>",        desc: "price watchlist with change detection" }
endpoints:   { module: endpoints.py,    args: "list [--pattern X]",                                                    desc: "list bundled registry/endpoints.json" }
twister:     { module: twister_api.py,  args: "<ASIN|URL> [-f raw|json] [-o file]",                                   desc: "twisterDimensionSlotsDefault AJAX" }
```

## Execution

```yaml
deps: ["python3", "curl_cffi (pip install curl_cffi)"]
on_invoke:
  1_deps: "pip install curl_cffi (if missing)"
  2_run: "python3 scripts/amazon.py <subcommand> <args>"
  3_verify: "bash tests/smoke.sh"
```

## Decision tree

```yaml
user_wants_product_data:
  has_asin_or_url: "python3 scripts/amazon.py rip <target> -f json"
  has_search_query: "python3 scripts/amazon.py search <query>"
  else: "ask for ASIN, URL, or search terms"

user_wants_reviews:
  quick: "python3 scripts/amazon.py reviews <ASIN>"
  deep:  "python3 scripts/amazon.py review-deep <ASIN> --pages 10 --star critical --sort recent"

user_wants_category: "python3 scripts/amazon.py category <node_id> --sort price-asc --prime --min-rating 4"
user_wants_rankings:  "python3 scripts/amazon.py bestsellers [dept] --feed best|new|movers|wished|gifted"
user_wants_deals:     "python3 scripts/amazon.py deals -n 50"
user_wants_seller:    "python3 scripts/amazon.py seller <seller_id>"
user_wants_variations: "python3 scripts/amazon.py variations <ASIN>"

user_wants_bulk:
  has_asin_list: "python3 scripts/amazon.py batch <file> -f csv -d 1.5"
  has_url: "python3 scripts/amazon.py harvest <url> --pages N -o asins.txt -> then batch"

user_wants_price_tracking:
  add:     "python3 scripts/amazon.py track add <ASIN> --label 'name'"
  check:   "python3 scripts/amazon.py track check"
  history: "python3 scripts/amazon.py track history <ASIN>"

captcha_hit:
  action: "built-in exponential backoff + session reset"
  if_persistent: "refresh registry/frozen-profile.json from a new browser HAR (headers + impersonate)"

curl_cffi_missing:
  action: "pip install curl_cffi"
```

