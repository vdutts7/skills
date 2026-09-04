#!/usr/bin/env bash

# smoke test: verify all subcommands parse without crashing

set -e

cd "$(dirname "$0")/../scripts"

echo "=== CLI help ==="

python3 amazon.py --help

echo ""

echo "=== subcommand help ==="

for cmd in rip search reviews review-deep category bestsellers deals seller variations harvest batch track twister; do

    python3 amazon.py $cmd --help > /dev/null 2>&1 && echo "  $cmd: OK" || echo "  $cmd: FAIL"

done

python3 amazon.py endpoints refresh --help > /dev/null 2>&1 && echo "  endpoints refresh: OK" || echo "  endpoints refresh: FAIL"

python3 amazon.py endpoints list --help > /dev/null 2>&1 && echo "  endpoints list: OK" || echo "  endpoints list: FAIL"

echo ""

echo "=== import check ==="

python3 -c "

import sys; sys.path.insert(0, '.')

from product import rip_product, cmd_rip, cmd_variations, enumerate_variations

from search import search_amazon, cmd_search, cmd_category, browse_category

from reviews import rip_reviews, cmd_reviews, cmd_review_deep, blast_reviews_deep

from feeds import cmd_bestsellers, cmd_deals, blast_bestsellers, blast_deals

from seller import cmd_seller, blast_seller

from track import cmd_track, cmd_track_add, cmd_track_check, cmd_track_history

from endpoints import harvest_har_dir, cmd_endpoints

from twister_api import cmd_twister, build_twister_url

print('All imports OK')

"

echo ""

echo "=== smoke passed ==="

