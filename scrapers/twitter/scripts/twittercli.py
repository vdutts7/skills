#!/usr/bin/env python3
"""
x-stingray - X/Twitter CLI. Zero auth default. Optional cookie boost.
Rotating guest tokens. Cascading resolvers. DDG query rotation.
Self-bootstrapping session cookies. Auto query ID refresh from JS bundle.

Modes:
  x-stingray.py --tweet ID|URL             Single tweet (cascade: GQL -> fxtwitter)
  x-stingray.py --search QUERY             Search (DDG site:x.com -> resolve)
  x-stingray.py --search QUERY --deep      Deep search (rotated keyword queries)
  x-stingray.py --user HANDLE              Profile + top ~99 tweets
  x-stingray.py --user HANDLE --exhaust    Profile + GQL tweets + DDG sweep
  x-stingray.py --users FILE|h1,h2,...     Multiple users (file or CSV)
  x-stingray.py --trends [--woeid N]       Trending topics
  x-stingray.py --refresh-qids             Refresh query IDs from x.com JS bundle

Auth boost (optional - unlocks search/detail/pagination):
  x-stingray.py --search QUERY --cookie-file cookies.json
  x-stingray.py --help-auth                Show cookie setup instructions

Options:
  --output DIR         Output directory (default: ./x-data)
  --max-results N      Max results (default: 50)
  --delay SECS         Delay between requests (default: 1.0)
  --no-resume          Don't resume multi-user
  --json               Stdout JSON, no file
  --profile-only       Skip tweets on --user
  --deep               Rotated multi-query search
  --exhaust            GQL + DDG sweep for max tweets
  --workers N          Parallel resolve workers (default: 1)
  --debug              Print raw responses
  --dry-run            Print plan only

"""

import argparse, json, os, re, sys, time, signal, subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote as urlquote
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- constants ---

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs=1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

UA_POOL = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

# Fallback QIDs (auto-refreshed via --refresh-qids)
DEFAULT_QIDS = {
    "UserByScreenName": "IGgvgiOx4QZndDHuD3x9TQ",
    "UserTweets": "36rb3Xj3iJ64Q-9wKDjCcQ",
    "TweetResultByRestId": "2Acdg-VztGlHX7MjX67Ysw",
    "TweetDetail": "oCon7R-cgWRFy6EfZjaKfg",
    "SearchTimeline": "Yw6L66Pw54NHKuq4Dp7b4Q",
}

FEATURES = '{"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"communities_web_enable_tweet_community_results_fetch":true,"c9s_tweet_anatomy_moderator_badge_enabled":true,"articles_preview_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}'
FEATURES_USER = '{"hidden_profile_subscriptions_enabled":true,"rweb_tipjar_consumption_enabled":true,"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":true,"subscriptions_verification_info_verified_since_enabled":true,"highlights_tweets_tab_ui_enabled":true,"responsive_web_twitter_article_notes_tab_enabled":true,"subscriptions_feature_can_gift_premium":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":true}'

AUTH_HELP = """
=== Cookie Auth Setup (optional - unlocks search + tweet detail + pagination) ===

1. Log in to x.com in browser
2. DevTools (F12) -> Application -> Cookies -> https://x.com
3. Copy: auth_token (40 hex), ct0 (32 hex)
4. Create cookies.json:  {"auth_token": "...", "ct0": "..."}
5. Run: x-stingray.py --search "query" --cookie-file cookies.json

Without cookies: profiles, ~99 tweets/user, trends, DDG search
With cookies: full search, tweet detail, pagination, all timelines
"""

# --- globals ---

_shutdown = False
_circuit = {"fails": 0, "open_until": 0}
_req_count = 0
_debug = False
_qids = dict(DEFAULT_QIDS)
_cookie_jar = "/tmp/x_stingray_cookies.txt"
_auth_cookies = None  # {auth_token, ct0} if --cookie-file provided


# --- token pool ---

class TokenPool:
    def __init__(self, rotate_every=15):
        self._tokens, self._idx = [], 0
        self._rotate_every = rotate_every
        self._calls = 0
        self._ua_idx = 0

    def get(self):
        if not self._tokens or self._calls >= self._rotate_every:
            self._mint()
            self._calls = 0
        self._calls += 1
        return self._tokens[self._idx]

    def _mint(self):
        body, code = _curl("https://api.x.com/1.1/guest/activate.json",
            headers={"Authorization": f"Bearer {BEARER}", "User-Agent": self.ua()},
            method="POST", use_jar=True)
        if code == 200:
            try:
                t = json.loads(body)["guest_token"]
                self._tokens.append(t)
                self._idx = len(self._tokens) - 1
                if len(self._tokens) > 10:
                    self._tokens = self._tokens[-5:]
                    self._idx = len(self._tokens) - 1
                return
            except: pass
        die("guest token mint failed")

    def ua(self):
        self._ua_idx = (self._ua_idx + 1) % len(UA_POOL)
        return UA_POOL[self._ua_idx]

    def force_rotate(self):
        self._calls = self._rotate_every


_pool = TokenPool()


# --- signals ---

def _sig(s, f):
    global _shutdown; _shutdown = True; log("shutdown...")
signal.signal(signal.SIGINT, _sig)
signal.signal(signal.SIGTERM, _sig)


# --- logging ---

def log(m): print(f"[{datetime.now().strftime('%H:%M:%S')}] {m}", file=sys.stderr)
def die(m): log(f"FATAL: {m}"); sys.exit(1)
def dbg(m):
    if _debug: log(f"[DBG] {m}")
def now_iso(): return datetime.now(timezone.utc).isoformat()


# --- session bootstrap (IG ripper pattern) ---

def bootstrap_session():
    """GET x.com/ to populate cookie jar - like the IG ripper's GET / for csrf."""
    _curl("https://x.com/", use_jar=True, save_jar=True)
    dbg("session bootstrapped")


# --- curl ---

def _curl(url, headers=None, method="GET", max_time=15, use_jar=False, save_jar=False):
    if _circuit["fails"] >= 5 and time.time() < _circuit["open_until"]:
        return "", 503
    cmd = ["curl", "-sS", "-w", "\n__XHTTP:%{http_code}__", "--max-time", str(max_time), "-L"]
    if method == "POST": cmd += ["-X", "POST"]
    if use_jar: cmd += ["-b", _cookie_jar]
    if save_jar: cmd += ["-c", _cookie_jar]
    # auth cookies override
    if _auth_cookies:
        cmd += ["-H", f"Cookie: auth_token={_auth_cookies['auth_token']}; ct0={_auth_cookies['ct0']}"]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=max_time + 5)
        out = r.stdout
        if "__XHTTP:" in out:
            parts = out.rsplit("__XHTTP:", 1)
            body, code = parts[0].strip(), int(parts[1].replace("__","").strip())
        else: body, code = out, 0
    except Exception as e: body, code = str(e), 0

    if code >= 500 or code == 0:
        _circuit["fails"] += 1
        if _circuit["fails"] >= 5:
            _circuit["open_until"] = time.time() + 30; log("circuit OPEN 30s")
    else: _circuit["fails"] = max(0, _circuit["fails"] - 1)
    global _req_count; _req_count += 1
    return body, code

def curl_json(url, headers=None, method="GET"):
    body, code = _curl(url, headers, method)
    if code == 200:
        try: return json.loads(body), code
        except: return None, code
    return None, code


# --- graphql ---

def gql_headers():
    gt = _pool.get()
    h = {"Authorization": f"Bearer {BEARER}", "x-guest-token": gt,
         "User-Agent": _pool.ua(), "x-twitter-active-user": "yes",
         "x-twitter-client-language": "en"}
    if _auth_cookies:
        h["x-csrf-token"] = _auth_cookies["ct0"]
    return h

def gql(endpoint, variables, features=None):
    feat = features or FEATURES
    qid = _qids.get(endpoint)
    if not qid: return None, 404
    url = f"https://api.x.com/graphql/{qid}/{endpoint}?variables={urlquote(json.dumps(variables))}&features={urlquote(feat)}"
    for attempt in range(3):
        body, code = _curl(url, headers=gql_headers(), use_jar=True)
        if code == 200:
            try:
                d = json.loads(body)
                dbg(f"GQL {endpoint}: 200, keys={list(d.get('data',{}).keys())}")
                return d, code
            except: return None, code
        elif code == 429:
            _pool.force_rotate(); w = 2 ** (attempt+1)
            log(f"429, rotate, wait {w}s..."); time.sleep(w)
        else:
            dbg(f"GQL {endpoint}: HTTP {code}")
            return None, code
    return None, 429


# --- tweet extraction ---

def extract_tweet(result):
    if not result or not isinstance(result, dict): return None
    if result.get("__typename") == "TweetWithVisibilityResults": result = result.get("tweet", {})
    if result.get("__typename") == "TweetTombstone": return None
    legacy = result.get("legacy", {})
    text = legacy.get("full_text") or legacy.get("text", "")
    nt = result.get("note_tweet",{}).get("note_tweet_results",{}).get("result",{})
    if nt.get("text"): text = nt["text"]
    if not text: return None
    core = result.get("core",{}).get("user_results",{}).get("result",{})
    al = core.get("legacy",{}); ic = core.get("core",{})
    sn = al.get("screen_name") or ic.get("screen_name") or "?"
    nm = al.get("name") or ic.get("name") or "?"
    tid = legacy.get("id_str") or result.get("rest_id","")
    return {"id":tid,"text":text,"screen_name":sn,"name":nm,
        "created_at":legacy.get("created_at",""),
        "likes":legacy.get("favorite_count",0),"retweets":legacy.get("retweet_count",0),
        "replies":legacy.get("reply_count",0),"quotes":legacy.get("quote_count",0),
        "bookmarks":legacy.get("bookmark_count",0),
        "views":result.get("views",{}).get("count","?"),
        "url":f"https://x.com/{sn}/status/{tid}",
        "lang":legacy.get("lang",""),
        "replying_to":legacy.get("in_reply_to_screen_name"),
        "replying_to_status":legacy.get("in_reply_to_status_id_str"),
        "conversation_id":legacy.get("conversation_id_str",""),
        "is_note_tweet":bool(nt.get("text")),
        "media":[m.get("media_url_https",m.get("url","")) for m in legacy.get("entities",{}).get("media",[])],
        "source":"graphql"}

def extract_fxtweet(data, tweet_id=""):
    t = data.get("tweet")
    if not t: return None
    a = t.get("author",{})
    v = a.get("verification",{})
    return {"id":str(t.get("id",tweet_id)),"text":t.get("text",""),
        "screen_name":a.get("screen_name","?"),"name":a.get("name","?"),
        "created_at":t.get("created_at",""),"created_timestamp":t.get("created_timestamp"),
        "likes":t.get("likes",0),"retweets":t.get("retweets",0),
        "replies":t.get("replies",0),"quotes":t.get("quotes",0),
        "bookmarks":t.get("bookmarks",0),"views":t.get("views","?"),
        "url":t.get("url",f"https://x.com/i/status/{tweet_id}"),
        "lang":t.get("lang",""),"tweet_source":t.get("source",""),
        "is_note_tweet":t.get("is_note_tweet",False),
        "community_note":t.get("community_note"),
        "replying_to":t.get("replying_to"),"replying_to_status":t.get("replying_to_status"),
        "media":[m.get("url","") for m in t.get("media",{}).get("all",[])],
        "author":{"id":a.get("id",""),"screen_name":a.get("screen_name",""),
            "name":a.get("name",""),"description":a.get("description",""),
            "followers":a.get("followers",0),"following":a.get("following",0),
            "likes":a.get("likes",0),"media_count":a.get("media_count",0),
            "avatar":a.get("avatar_url",""),"banner":a.get("banner_url",""),
            "joined":a.get("joined",""),"verified":v.get("verified",False),
            "verified_type":v.get("type","")},
        "source":"fxtwitter"}


# --- resolution cascade ---

def resolve_tweet(tweet_id, handle="i"):
    """fxtwitter first (richer: bookmarks, author, source) -> GQL fallback."""
    fx, fc = curl_json(f"https://api.fxtwitter.com/{handle}/status/{tweet_id}",headers={"User-Agent":_pool.ua()})
    if fx:
        t = extract_fxtweet(fx, tweet_id)
        if t and t["text"]: return t
    time.sleep(0.3)
    d, c = gql("TweetResultByRestId",{"tweetId":tweet_id,"withCommunity":False,"includePromotedContent":False,"withVoice":False})
    if d:
        tr = d.get("data",{}).get("tweetResult",{}).get("result")
        t = extract_tweet(tr)
        if t and t["text"]: return t
    return None

def resolve_batch(candidates, delay=0.5, workers=1):
    """Resolve list of {id,handle}. Parallel if workers>1."""
    resolved, failed = [], []
    if workers <= 1:
        for c in candidates:
            if _shutdown: break
            t = resolve_tweet(c["id"], c.get("handle","i"))
            (resolved if t else failed).append(t or c)
            time.sleep(delay)
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(resolve_tweet, c["id"], c.get("handle","i")): c for c in candidates}
            for fut in as_completed(futs):
                c = futs[fut]
                try:
                    t = fut.result()
                    (resolved if t else failed).append(t or c)
                except: failed.append(c)
    return resolved, failed

def parse_tweet_id(raw):
    raw = raw.strip()
    m = re.search(r'(?:twitter\.com|x\.com)/(\w+)/status/(\d+)', raw)
    if m: return m.group(2), m.group(1)
    if raw.isdigit(): return raw, "i"
    return None, None


# --- DDG search ---

def ddg_search(query, max_results=50):
    ensure_ddgs()
    from ddgs import DDGS
    ddgs = DDGS()
    for attempt in range(3):
        try:
            raw = list(ddgs.text(query, max_results=max_results))
            break
        except Exception as e:
            if attempt < 2: time.sleep(2 ** (attempt+1)); continue
            else: log(f"DDG failed: {e}"); return []
    seen, results = set(), []
    for r in raw:
        m = re.search(r'x\.com/(\w+)/status/(\d+)', r.get("href",""))
        if m and m.group(2) not in seen:
            seen.add(m.group(2))
            results.append({"handle":m.group(1),"id":m.group(2),"url":r.get("href",""),
                "snippet":r.get("body",""),"title":r.get("title","")})
    return results

def ddg_rotated(base_query, keywords=None, max_per=50, delay=2.0):
    if keywords is None:
        keywords = ["","2025","2024","2026","thread","announcement","opinion","news","update","release","AI","launch","guide","analysis"]
    all_r, stats, stale = {}, [], 0
    for kw in keywords:
        if _shutdown: break
        q = f"site:x.com {base_query} {kw}".strip()
        before = len(all_r)
        for r in ddg_search(q, max_results=max_per):
            if r["id"] not in all_r: all_r[r["id"]] = r
        new = len(all_r) - before
        stats.append({"query":q,"new":new})
        log(f"  [{len(all_r):3d} unique] {q} -> {new} new")
        stale = stale + 1 if new == 0 else 0
        if stale >= 3: log("  stale, stopping rotation"); break
        time.sleep(delay)
    return list(all_r.values()), stats


# --- commands ---

def cmd_tweet(args):
    tid, handle = parse_tweet_id(args.tweet)
    if not tid: die(f"bad ID: {args.tweet}")
    log(f"tweet {tid}...")
    t = resolve_tweet(tid, handle)
    if not t: die(f"tweet {tid} unreachable")
    output(args, {"tweet":t,"fetched_at":now_iso(),"requests":_req_count}, f"tweet_{tid}.json")
    if not args.json: print_tweet(t)

def cmd_search(args):
    query, mr = args.search, args.max_results
    if args.deep:
        log(f"DEEP search: {query}")
        candidates, stats = ddg_rotated(query, max_per=mr, delay=args.delay)
    else:
        log(f"search: site:x.com {query}")
        candidates = ddg_search(f"site:x.com {query}", max_results=mr)
        stats = [{"query":f"site:x.com {query}","new":len(candidates)}]
    log(f"{len(candidates)} candidates, resolving (workers={args.workers})...")
    resolved, failed = resolve_batch(candidates[:mr], delay=args.delay*0.5, workers=args.workers)
    for c in failed:
        resolved.append({"id":c.get("id",""),"text":c.get("snippet",""),"screen_name":c.get("handle","?"),
            "name":"?","url":c.get("url",""),"source":"ddg_snippet","likes":"?","retweets":"?","views":"?"})
    result = {"query":query,"deep":args.deep,"results":resolved,"total_candidates":len(candidates),
        "resolved_full":len(resolved)-len(failed),"resolved_snippet":len(failed),
        "query_stats":stats,"fetched_at":now_iso(),"requests":_req_count}
    slug = re.sub(r'\W+','_',query)[:40]
    output(args, result, f"search_{slug}.json")
    if not args.json:
        for t in [r for r in resolved if r.get("source") != "ddg_snippet"]:
            print_tweet(t); print()

def cmd_user(args, handles=None):
    if handles is None: handles = [args.user.lstrip("@")]
    sp = Path(args.output) / ".user_state.json"
    done = set()
    if not args.no_resume and sp.exists():
        try: done = set(json.loads(sp.read_text()).get("completed",[]))
        except: pass
    for h in handles:
        if _shutdown: break
        if h in done: log(f"skip {h}"); continue
        log(f"@{h}...")
        result = fetch_user(h, profile_only=args.profile_only, delay=args.delay)
        if not result: log(f"  FAILED: @{h}"); continue
        if args.exhaust and not args.profile_only:
            gc = len(result.get("tweets",[]))
            gids = {t["id"] for t in result.get("tweets",[])}
            log(f"  EXHAUST: GQL={gc}, sweeping DDG...")
            bio = result.get("profile",{}).get("description","")
            bw = [w for w in re.findall(r'\w+',bio.lower()) if len(w)>3 and w not in {"https","http","just","that","this","with","from","have","been"}][:5]
            cands, qs = ddg_rotated(f"from:{h}", keywords=[""]+["2025","2024","2023","thread"]+bw, max_per=50, delay=args.delay)
            new = [c for c in cands if c["id"] not in gids]
            log(f"  EXHAUST: {len(cands)} DDG, {len(new)} new")
            if new:
                res, _ = resolve_batch(new, delay=args.delay*0.5, workers=args.workers)
                log(f"  EXHAUST: +{len(res)} tweets")
                result["tweets"] = result.get("tweets",[]) + res
                result["tweet_count"] = len(result["tweets"])
                result["exhaust_stats"] = {"gql":gc,"ddg_total":len(cands),"ddg_new":len(new),"ddg_resolved":len(res),"total":len(result["tweets"]),"queries":qs}
        if args.json and len(handles) == 1:
            json.dump(result, sys.stdout, indent=2, ensure_ascii=False); print()
        else:
            od = Path(args.output); od.mkdir(parents=True, exist_ok=True)
            atomic_write(od/f"{h}.json", result); log(f"saved {od}/{h}.json")
        done.add(h)
        if len(handles) > 1: atomic_write(sp, {"completed":list(done)})
        time.sleep(args.delay)

def cmd_users(args):
    raw = args.users
    if os.path.isfile(raw): hs = [l.strip().lstrip("@") for l in open(raw) if l.strip() and not l.startswith("#")]
    else: hs = [h.strip().lstrip("@") for h in raw.split(",") if h.strip()]
    if not hs: die("no handles")
    log(f"batch: {len(hs)} users"); cmd_user(args, handles=hs)

def cmd_trends(args):
    woeid = args.woeid or 1
    log(f"trends (woeid={woeid})...")
    d, c = curl_json(f"https://api.x.com/1.1/trends/place.json?id={woeid}", headers=gql_headers())
    if not d: die(f"trends: HTTP {c}")
    trends = d[0].get("trends",[]) if isinstance(d,list) else []
    result = {"woeid":woeid,"location":d[0].get("locations",[{}])[0].get("name","?") if isinstance(d,list) else "?",
        "trends":[{"name":t["name"],"url":t.get("url",""),"tweet_volume":t.get("tweet_volume")} for t in trends],
        "fetched_at":now_iso()}
    output(args, result, f"trends_{woeid}.json")
    if not args.json:
        for i, t in enumerate(trends[:30],1):
            v = f" ({t['tweet_volume']:,})" if t.get("tweet_volume") else ""
            print(f"  {i:2d}. {t['name']}{v}")

def cmd_refresh_qids(args):
    """Blast x.com JS bundle for current query IDs."""
    log("refreshing query IDs from x.com production JS...")
    body, code = _curl("https://x.com", headers={"User-Agent":UA_POOL[0]})
    if code != 200: die(f"GET x.com: HTTP {code}")
    js_urls = re.findall(r'https://abs\.twimg\.com/responsive-web/client-web/main\.[a-f0-9]+\.js', body)
    if not js_urls: die("no main.js URL found")
    js_body, jc = _curl(js_urls[0], headers={"User-Agent":UA_POOL[0]})
    if jc != 200: die(f"GET main.js: HTTP {jc}")
    pairs = re.findall(r'queryId:"([^"]+)",operationName:"([^"]+)"', js_body)
    updated = {}
    targets = ["UserByScreenName","UserTweets","TweetResultByRestId","TweetDetail","SearchTimeline",
               "TweetResultsByRestIds","UserTweetsAndReplies","UserMedia","Followers","Following","Likes"]
    for qid, name in pairs:
        if name in targets: updated[name] = qid
    log(f"extracted {len(updated)} query IDs:")
    for n, q in sorted(updated.items()):
        marker = " (UPDATED)" if n in _qids and _qids[n] != q else ""
        log(f"  {n}: {q}{marker}")
    outpath = Path(args.output) / "qids.json"
    Path(args.output).mkdir(parents=True, exist_ok=True)
    atomic_write(outpath, {"qids":updated,"extracted_at":now_iso(),"source":js_urls[0]})
    log(f"saved to {outpath}")


# --- user fetch ---

def fetch_user(handle, profile_only=False, delay=1.0):
    d, c = gql("UserByScreenName",{"screen_name":handle,"withSafetyModeUserFields":True}, features=FEATURES_USER)
    if not d: return None
    try: user = d["data"]["user"]["result"]
    except: return None
    leg = user.get("legacy",{}); core = user.get("core",{}); av = user.get("avatar",{}); loc = user.get("location",{})
    sn = core.get("screen_name") or leg.get("screen_name") or handle
    profile = {"id":user.get("rest_id",""),"screen_name":sn,
        "name":core.get("name") or leg.get("name") or "?",
        "description":leg.get("description",""),"location":loc.get("location","") or leg.get("location",""),
        "followers":leg.get("followers_count",0),"following":leg.get("friends_count",0),
        "tweets_count":leg.get("statuses_count",0),
        "created_at":core.get("created_at") or leg.get("created_at") or "",
        "verified":user.get("is_blue_verified",False),
        "avatar":(av.get("image_url","") or leg.get("profile_image_url_https","")).replace("_normal","_400x400"),
        "banner":leg.get("profile_banner_url",""),"url":f"https://x.com/{sn}"}
    result = {"profile":profile,"fetched_at":now_iso()}
    if profile_only: return result
    time.sleep(delay)
    uid = profile["id"]
    if not uid: return result
    td, tc = gql("UserTweets",{"userId":uid,"count":100,"includePromotedContent":False,
        "withQuickPromoteEligibilityTweetFields":True,"withVoice":True,"withV2Timeline":True})
    if td:
        try:
            ur = td["data"]["user"]["result"]
            tl = ur.get("timeline_v2", ur.get("timeline",{}))
            inner = tl.get("timeline", tl)
            tweets = []
            for inst in inner.get("instructions",[]):
                for e in inst.get("entries",[]):
                    tr = e.get("content",{}).get("itemContent",{}).get("tweet_results",{}).get("result")
                    t = extract_tweet(tr)
                    if t: tweets.append(t)
            result["tweets"] = tweets; result["tweet_count"] = len(tweets)
        except Exception as e: log(f"  tweet parse: {e}")
    return result


# --- display ---

def print_tweet(t):
    src = f" [{t.get('source','')}]" if t.get("source") else ""
    print(f"@{t.get('screen_name','?')} ({t.get('name','?')}){src}")
    print(f"  {t.get('text','')}")
    bk = t.get("bookmarks","")
    bk_str = f"  🔖 {bk}" if bk else ""
    print(f"  ♥ {t.get('likes','?')}  🔁 {t.get('retweets','?')}  💬 {t.get('replies','?')}  👁 {t.get('views','?')}{bk_str}")
    if t.get("created_at"): print(f"  {t['created_at']}")
    if t.get("url"): print(f"  {t['url']}")


# --- utilities ---

def atomic_write(path, data):
    p = Path(path); tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False)); tmp.rename(p)

def output(args, data, name):
    if args.json: json.dump(data, sys.stdout, indent=2, ensure_ascii=False); print()
    else:
        od = Path(args.output); od.mkdir(parents=True, exist_ok=True)
        atomic_write(od/name, data); log(f"saved {od}/{name}")

def ensure_ddgs():
    try: import ddgs; return
    except ImportError: pass
    try: from duckduckgo_search import DDGS; return
    except ImportError: pass
    log("installing ddgs...")
    subprocess.run([sys.executable,"-m","pip","install","-q","ddgs","--break-system-packages"],capture_output=True,timeout=60)

def load_qids(args):
    """Load cached QIDs from disk if available."""
    global _qids
    p = Path(args.output) / "qids.json"
    if p.exists():
        try:
            d = json.loads(p.read_text())
            _qids.update(d.get("qids",{}))
            dbg(f"loaded {len(d.get('qids',{}))} cached QIDs")
        except: pass


# --- main ---

def main():
    p = argparse.ArgumentParser(description="x-stingray: X/Twitter CLI (anon)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--tweet", metavar="ID|URL")
    g.add_argument("--search", metavar="QUERY")
    g.add_argument("--user", metavar="HANDLE")
    g.add_argument("--users", metavar="FILE|CSV")
    g.add_argument("--trends", action="store_true")
    g.add_argument("--refresh-qids", action="store_true")
    g.add_argument("--help-auth", action="store_true")

    p.add_argument("--output", default="./x-data")
    p.add_argument("--max-results", type=int, default=50)
    p.add_argument("--delay", type=float, default=1.0)
    p.add_argument("--woeid", type=int)
    p.add_argument("--no-resume", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--profile-only", action="store_true")
    p.add_argument("--deep", action="store_true")
    p.add_argument("--exhaust", action="store_true")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--debug", action="store_true")
    p.add_argument("--cookie-file", metavar="FILE")
    p.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    global _debug, _auth_cookies
    _debug = args.debug

    if args.help_auth:
        print(AUTH_HELP); return

    # Load auth cookies if provided
    if args.cookie_file:
        try:
            _auth_cookies = json.loads(Path(args.cookie_file).read_text())
            log(f"auth cookies loaded (ct0={_auth_cookies['ct0'][:8]}...)")
        except Exception as e:
            die(f"cookie-file error: {e}")

    if args.dry_run:
        log("DRY RUN:")
        if args.tweet: log(f"  tweet: {args.tweet}")
        elif args.search: log(f"  search: {args.search} {'(deep)' if args.deep else ''}")
        elif args.user: log(f"  user: {args.user} {'(exhaust)' if args.exhaust else ''}")
        elif args.users: log(f"  users: {args.users}")
        elif args.trends: log(f"  trends")
        elif args.refresh_qids: log(f"  refresh-qids")
        return

    # Load cached QIDs
    load_qids(args)

    # Bootstrap session (IG ripper pattern: GET / for cookies)
    bootstrap_session()

    if args.refresh_qids: cmd_refresh_qids(args)
    elif args.tweet: cmd_tweet(args)
    elif args.search: cmd_search(args)
    elif args.user: cmd_user(args)
    elif args.users: cmd_users(args)
    elif args.trends: cmd_trends(args)

    log(f"done. {_req_count} requests.")


if __name__ == "__main__":
    main()
