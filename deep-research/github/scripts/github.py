#!/usr/bin/env python3
"""
github.py - GitHub public API CLI
Usage:
  github.py repo <owner/name>
  github.py user <username>
  github.py search '<query>' [--type repos|users] [--max N]
  github.py releases <owner/name> [--max 5]
  github.py issues <owner/name> [--max 20] [--state open|closed]

Set GITHUB_TOKEN env var for higher rate limits (5000/hr vs 60/hr).
"""
import sys
import os
import json
import argparse
import urllib.request
import urllib.parse

API = "https://api.github.com"


def headers() -> dict:
    h = {"Accept": "application/vnd.github.v3+json", "User-Agent": "github-skill/1.0"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def get(path: str) -> dict | list:
    url = API + path
    req = urllib.request.Request(url, headers=headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body).get("message", body)
        except Exception:
            msg = body
        print(json.dumps({"error": msg, "status": e.code}))
        sys.exit(1)


def cmd_repo(args):
    owner, name = args.repo.split("/", 1)
    data = get(f"/repos/{owner}/{name}")
    out = {
        "full_name": data.get("full_name"),
        "description": data.get("description"),
        "stars": data.get("stargazers_count"),
        "forks": data.get("forks_count"),
        "open_issues": data.get("open_issues_count"),
        "language": data.get("language"),
        "license": (data.get("license") or {}).get("spdx_id"),
        "topics": data.get("topics", []),
        "updated_at": data.get("updated_at", "")[:10],
        "homepage": data.get("homepage"),
        "html_url": data.get("html_url"),
    }
    print(json.dumps(out, indent=2))


def cmd_user(args):
    data = get(f"/users/{args.username}")
    repos = get(f"/users/{args.username}/repos?per_page=10&sort=updated")
    out = {
        "login": data.get("login"),
        "name": data.get("name"),
        "bio": data.get("bio"),
        "company": data.get("company"),
        "location": data.get("location"),
        "public_repos": data.get("public_repos"),
        "followers": data.get("followers"),
        "html_url": data.get("html_url"),
        "top_repos": [
            {"name": r["name"], "stars": r["stargazers_count"], "language": r["language"]}
            for r in repos[:10]
        ],
    }
    print(json.dumps(out, indent=2))


def cmd_search(args):
    q = urllib.parse.quote(args.query)
    t = args.type
    endpoint = f"/search/{t}?q={q}&per_page={args.max}&sort=stars&order=desc"
    data = get(endpoint)
    items = data.get("items", [])
    if t == "repositories":
        out = [
            {
                "full_name": r["full_name"],
                "description": r["description"],
                "stars": r["stargazers_count"],
                "language": r["language"],
                "url": r["html_url"],
            }
            for r in items
        ]
    elif t == "users":
        out = [{"login": r["login"], "url": r["html_url"]} for r in items]
    else:
        out = items
    print(json.dumps(out, indent=2))


def cmd_releases(args):
    owner, name = args.repo.split("/", 1)
    data = get(f"/repos/{owner}/{name}/releases?per_page={args.max}")
    out = [
        {
            "tag": r["tag_name"],
            "name": r["name"],
            "published": r["published_at"][:10] if r.get("published_at") else "",
            "prerelease": r["prerelease"],
            "url": r["html_url"],
        }
        for r in data
    ]
    print(json.dumps(out, indent=2))


def cmd_issues(args):
    owner, name = args.repo.split("/", 1)
    data = get(f"/repos/{owner}/{name}/issues?state={args.state}&per_page={args.max}")
    out = [
        {
            "number": i["number"],
            "title": i["title"],
            "state": i["state"],
            "created": i["created_at"][:10],
            "user": i["user"]["login"],
            "url": i["html_url"],
            "labels": [l["name"] for l in i.get("labels", [])],
        }
        for i in data
        if "pull_request" not in i  # exclude PRs
    ]
    print(json.dumps(out, indent=2))


def main():
    p = argparse.ArgumentParser(description="GitHub public API CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("repo", help="fetch repo metadata")
    r.add_argument("repo", metavar="owner/name")

    u = sub.add_parser("user", help="fetch user profile")
    u.add_argument("username")

    s = sub.add_parser("search", help="search repos/users")
    s.add_argument("query")
    s.add_argument("--type", choices=["repositories", "users"], default="repositories")
    s.add_argument("--max", type=int, default=10)

    rl = sub.add_parser("releases", help="list releases")
    rl.add_argument("repo", metavar="owner/name")
    rl.add_argument("--max", type=int, default=5)

    i = sub.add_parser("issues", help="list issues")
    i.add_argument("repo", metavar="owner/name")
    i.add_argument("--max", type=int, default=20)
    i.add_argument("--state", choices=["open", "closed", "all"], default="open")

    args = p.parse_args()
    dispatch = {
        "repo": cmd_repo,
        "user": cmd_user,
        "search": cmd_search,
        "releases": cmd_releases,
        "issues": cmd_issues,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
