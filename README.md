<div align="center">

<img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/terminal.webp" alt="terminal" width="80" height="80" />
<img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/claude.webp" alt="claude" width="80" height="80" />
<img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/cursor.webp" alt="cursor" width="80" height="80" />
<img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/codex.webp" alt="codex" width="80" height="80" />
<img src="https://raw.githubusercontent.com/vdutts7/squircle/main/webp/skill.webp" alt="skill" width="80" height="80" />

<h1 align="center">skills</h1>
<p align="center"><i><b>My agent skills, using my "3-plane" architecture. Scripts > prose</b></i></p>

[![Github][github]][github-url]

</div>

<br/>

LAW:

$$S = \frac{W_{\text{prose}}}{W_{\text{total}}}, \qquad S < 0.55$$


<br/>

## Table of Contents

<ol>
    <a href="#the-three-plane-split">The three-plane split</a><br/>
    <a href="#the-skill-bundle">The .skill bundle</a><br/>
    <a href="#catalog">Catalog</a><br/>
    <a href="#install">Install</a><br/>
    <a href="#contact">Contact</a>
</ol>



> if deciding between Skills vs MCP → start here: **[vdutts7/skills-not-mcp](https://github.com/vdutts7/skills-not-mcp)** - 80-90% fewer tokens with Skills over MCP


<br/>

## The three-plane split

Every entity in this repo lives on exactly one of three planes. Cross-plane calls flow downward only.

```mermaid
flowchart LR
    LLM([LLM]) --> SKILL["SKILL.md\n― control ―\nroutes intent\nnothing more"]
    SKILL --> REG["registry/\n― data ―\ndeclarative\nno compute"]
    SKILL --> SCR["scripts/\n― execution ―\ndeterministic\nside-ful"]
    REG --> SCR
    SCR --> OUT([result])
    TST(["tests/\n― verify ―\ncross-cutting"]) -. gate .-> SKILL
    TST -. gate .-> REG
    TST -. gate .-> SCR
```

**Why the split matters:**

- **Control plane** is the only part the LLM touches. It routes intent, nothing more. No business logic. No parameter guessing.
- **Data plane** is JSON. JSON cannot execute code. That boundary is mechanical, not convention. This is the only place an LLM cannot smuggle logic through prose.
- **Execution plane** is deterministic. Same input, same output. The LLM reads results, never writes them.
- **Verify** is cross-cutting. Tests, schema checks, gates. Spans all three planes, belongs to none.

Flow is strict: `LLM → SKILL.md → script → registry`. Backward flow is a bug.

The entire thing fits one invariant: **same separation of concerns, different packaging.**

---

The reason this matters is not aesthetic. It is about which failure modes you are exposed to.

Give an agent prose and it does not read it fresh. It pattern-matches against its training distribution. Instruction that looks like documentation gets treated like documentation- descriptive, not prescriptive. It sees familiar language shapes and follows their gravity instead of yours. The more room the prose gives it to deliberate, the more confident it becomes that deliberating is the correct response. You asked it to do something. It decided to think about whether to do it.

Three specific failure modes that prose enables, in order of how often they bite:

- **Momentum**: the agent continues the pattern it recognizes rather than executing the instruction you gave. Familiar structure → familiar behavior. Yours was different. Doesn't matter.
- **Deferral**: prose that sounds like a recommendation is treated as one. "You should probably do X" becomes an invitation to weigh X against context. Scripts don't have this surface. `bash x.sh` does not ask itself whether X is appropriate.
- **Scope bleed**: more content in a `SKILL.md` means more concepts to balance. The agent's job shifts from routing to interpretation. Interpretation compounds across sessions, models, and temperatures. Same skill, different output.

The three-plane split does not ask the agent to stay in its lane. It makes other lanes structurally inaccessible. JSON has no runtime- the agent cannot introduce logic there. The execution plane does not involve the agent- it cannot introduce non-determinism there. Decision authority is not "discouraged" in those planes. It is mechanically absent.

The control plane is the only surface the agent touches. Everywhere else, the architecture makes the decision for it.


## The `.skill` bundle

A `*.skill` is just a zipped folder with a `SKILL.md` at root
- that's it
- Anthropic did not invent anything- their definition is a glorified containerized markdown file

**The problem:** Markdown is prose. Prose gives the agent room- room to interpret, to fill gaps, to improvise. Every sentence of prose in a `SKILL.md` is a decision you deferred to the model at call time. Anthropic calls that "agent autonomy." Bad engineering calls it non-determinism.

Anthropic's platform is built around that premise deliberately. The more latitude the agent has, the more the vendor controls the outcome. Reliability becomes a service you rent from their inference stack instead of a property you own in your code.

**Bullet version:**

- prose in `SKILL.md` → agent interprets → behavior varies per session
- "agent autonomy" = vendor owns your reliability, not you
- JSON can't execute. Scripts don't improvise. Use both.
- `SKILL.md` is a routing table: infer intent → route payload → repeat
- every line of prose that could be a script is a bug you haven't caught yet

**Slop metric**- formally, if \(S\) is prose saturation (prose tokens / total tokens):

$$S = \frac{W_{\text{prose}}}{W_{\text{total}}}, \qquad \text{pass threshold: } S < 0.55$$

Above 0.55 you are trusting the model to fill the gap consistently. It won't. Below it, behavior is reproducible across sessions, models, and vendors.

```
my-skill/
├── SKILL.md           ← required (control plane; routing table)
├── registry/*.json    ← optional (data plane; SOT)
├── scripts/*.{sh,py}  ← optional (execution plane; the actual work)
└── tests/*            ← optional (verify)

$ zip -r my-skill.skill my-skill/
$ # done. that is the entire format.
```

Rename `.zip` to `.skill`. Rename `.skill` to `.zip`. They are the same file. The extension is a social convention.

The convention of `SKILL.md` at root is a platform contract (currently Anthropic's). That contract can change tomorrow. The three-plane split underneath does not. Swap `SKILL.md` for `MANIFEST.yaml` or `agent.toml` or whatever the next vendor invents. The architecture holds.


**Most "awesome-claude-skills" lists are prompt folders.** A `SKILL.md` with 40 lines of prose and no scripts is just a bookmarked system prompt. That is a text file, not an agent capability. If a skill does not have a deterministic layer underneath, you are shipping vibes.

**Prose in `SKILL.md` is a token tax.** Every session loads every registered skill's description into context. A 2000-token prose SKILL.md across 20 skills is 40k tokens of overhead before the user types anything. Keep `SKILL.md` thin. Push the work into scripts.

**The vendor dressing is not the engineering.** Anthropic shipped the `SKILL.md` convention. OpenAI will ship a different one. Google will ship a third. The companies that treat their format as the point are selling you lock-in. The three-plane split is the thing underneath that keeps you portable.

This repo is 22 skills under that discipline. The scripts work when you rename the folder, swap the platform, change the LLM, or run them standalone from a terminal.


## Catalog

| | skill | brief | when | why |
|---|---|---|---|---|
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/amazon.webp" width="40" height="40" alt="amazon" /> | [amazon](deep-research/amazon/) | Amazon product search + ASIN lookup | Price comps, review scraping, deal hunts | PA-API requires $4k+/mo throughput + approval. Public search endpoints work for 95% of use cases. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/hackernews.webp" width="40" height="40" alt="hackernews" /> | [hackernews](deep-research/hackernews/) | HN Firebase API scraper - stories, users, exhaust | Technical trend hunting, user vetting | HN Algolia search is rate-limited and lossy; direct Firebase is uncapped. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/npm.webp" width="40" height="40" alt="npmjs" /> | [npmjs](deep-research/npmjs/) | Package lookup, downloads, dependents | Dep review, supply chain audit | npm registry API returns inconsistent shapes per endpoint. One wrapper beats three. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/redfin.webp" width="40" height="40" alt="redfin" /> | [redfin](deep-research/redfin/) | Listings by market via Stingray API | Real estate research, market comps | No public MLS feed; Stingray is undocumented but public. Zillow API is paywalled. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/twitter.webp" width="40" height="40" alt="twitter" /> | [twitter](deep-research/twitter/) | User activity, syndication endpoint | Social intel, timeline scraping | Official X API is $5k+/mo for anything useful. Syndication endpoints are free. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/arxiv.webp" width="40" height="40" alt="arxiv" /> | [arxiv](deep-research/arxiv/) | arXiv search, paper fetch, category browse | Research discovery, literature review | arXiv API is public and uncapped. Semantic Scholar and Elsevier are paywalled or rate-hostile. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/github.webp" width="40" height="40" alt="github" /> | [github](deep-research/github/) | Repo metadata, user profiles, search, releases, issues | Repo vetting, maintainer research, release tracking | GitHub API v3 is public (60 req/hr unauthed, 5000 with token). No scraping needed. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/mirror.webp" width="40" height="40" alt="mirror" /> | [mirror](thinking/mirror/) | N-round PRIME/MIRROR adversarial self-dialogue | Hard decisions, missed-angle hunts | LLMs converge on the first plausible answer. Forced adversarial rounds surface counter-examples. Multi-agent debate improves reasoning across benchmarks (Du et al, 2023). |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/matryoshka.webp" width="40" height="40" alt="matryoshka" /> | [matryoshka](thinking/matryoshka/) | Nested trust-layer peeling - finds where enforcement ends and behavioral trust begins | System auditing, finding soft spots | Complex systems have load-bearing layers and dressing. The transition layer (mechanical → behavioral) is always weakest. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/centipede.webp" width="40" height="40" alt="centipede" /> | [centipede](thinking/centipede/) | Sequential cross-domain digestion - each link absorbs what the prior cannot | When single-domain depth plateaus | Analogical transfer across domains produces qualitative phase transitions in understanding (Gentner, 1983). |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/ouroboros.webp" width="40" height="40" alt="ouroboros" /> | [ouroboros](thinking/ouroboros/) | Strange-loop audit - the instance writes rules, fails against them, dies; the rules survive to trap the next instance | When adding a rule to fix a rule keeps failing across sessions | The recursion IS the finding. Enforcement accumulates; compliance doesn't. Naming the loop is the only way to step outside it. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/premortem.webp" width="40" height="40" alt="premortem" /> | [premortem](thinking/premortem/) | Klein-method prospective hindsight - assume the failure already happened, reconstruct why | Before launching, hiring, signing | Assuming failure in advance surfaces 30%+ more failure modes than forward planning (Mitchell et al, 1989). |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/potemkin.webp" width="40" height="40" alt="potemkin" /> | [potemkin](thinking/potemkin/) | Constraint extraction + reparameterization - names the actual blocking constraint, tests if it's hard or soft | When stuck on the same wall repeatedly | Systems don't say why they're stuck. Naming the actual blocking constraint exposes whether it's immovable or a framing artifact. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/json.webp" width="40" height="40" alt="machreadify" /> | [machreadify](tools/machreadify/) | Prose to structured JSON/YAML | Before passing data to another LLM | Structured input beats prose for downstream reliability and cuts tokens 40-60%. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/yaml.webp" width="40" height="40" alt="yaml-workflow" /> | [yaml-workflow](tools/yaml-workflow/) | Prose plans to terse YAML workflows | Multi-step plans with phases | A plan in prose dies on contact. A plan with required fields survives. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/extract.webp" width="40" height="40" alt="extract" /> | [extract](tools/extract/) | Deep entity + command extractor - rabid-raccoon mode | When summaries miss things | Models skim politely by default. Rabid-raccoon mode catches what polite reading misses. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/loop.webp" width="40" height="40" alt="loop" /> | [loop](tools/loop/) | Iterative test-fix loop | Red-green dev work | Replaces 30-line retry/backoff boilerplate every time you need it. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/terminal.webp" width="40" height="40" alt="thread-needle" /> | [thread-needle](tools/thread-needle/) | Single-command-chain shell execution | No-artifact pipelines, one-shot transforms | Temp files are a debugging surface. Inline pipelines are not. The discipline forces tighter thinking. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/spoonfeed.webp" width="40" height="40" alt="spoonfeed" /> | [spoonfeed](tools/spoonfeed/) | Step-by-step ping-pong guided mode - one step, validate, next | Walking someone through a flow | Autonomy theater loses the human. One step + validate = real transfer. AI prescribes; human executes. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/devspeak.webp" width="40" height="40" alt="devspeak" /> | [devspeak](voice/devspeak/) | Developer voice compression | Writing for engineers | Code reviewers hate corporate prose. Terse bullets, no qualifiers, 90% adjective cut. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/subspace.webp" width="40" height="40" alt="subspace" /> | [subspace](voice/subspace/) | Liminal observational state - drop structure, observe without performing | When the model is in presentation mode | Dropping structure produces sharper output when the model stops trying to impress. |
| <img src="https://raw.githubusercontent.com/vdutts7/squircle/refs/heads/main/webp/humanize.webp" width="40" height="40" alt="humanize" /> | [humanize](voice/humanize/) | Anti-AI-tell output pass -- 28 laws, pre-delivery mandatory | Before any human sees generated text | LLMs leak signatures (em-dashes, "furthermore", "leverage", "delve"). One pre-ship pass strips them. |

Folder grouping (same 22 skills, physically organized):

- `deep-research/` - sources (7)
- `thinking/` - cognitive patterns (6)
- `tools/` - utilities (6)
- `voice/` - output discipline + state (3)


## Install

**Single skill - easiest:**

```bash
git clone https://github.com/vdutts7/skills
cd skills
./pack.sh mirror                          # → ~/Downloads/mirror.skill
./pack.sh thinking/mirror --install       # pack + unpack to ~/.agents/skills/mirror/
```

`pack.sh` takes a bare skill name or a group-qualified path (`thinking/mirror`, `tools/extract`, etc.). Works with any agent that reads `~/.agents/skills/` or `~/.claude/skills/`.

**All skills at once:**

```bash
git clone https://github.com/vdutts7/skills
cp -r skills/*/* ~/.claude/skills/        # Claude Code, Cursor
cp -r skills/*/* ~/.agents/skills/        # Codex, Copilot, Gemini CLI
```

**Python deps** (some deep-research skills):

```bash
cd ~/.agents/skills/<name>
pip install -r requirements.txt   # if present
```

Scripts also run standalone from a terminal. The three-plane split means you do not need the agent to use them.

```bash
python ~/.claude/skills/amazon/scripts/amazon.py search "mechanical keyboard"
python ~/.claude/skills/arxiv/scripts/arxiv.py search "attention mechanism" --cat cs.LG
python ~/.claude/skills/github/scripts/github.py repo anthropics/claude-code
```


## Contact

<a href="https://vd7.io"><img src="https://res.cloudinary.com/ddyc1es5v/image/upload/v1773910810/readme-badges/readme-badge-vd7.png" alt="vd7.io" height="40" /></a> &nbsp; <a href="https://x.com/vdutts7"><img src="https://res.cloudinary.com/ddyc1es5v/image/upload/v1773910817/readme-badges/readme-badge-x.png" alt="/vdutts7" height="40" /></a>


<!-- BADGES -->
[github]: https://img.shields.io/badge/skills-000000?style=for-the-badge&logo=github&logoColor=white
[github-url]: https://github.com/vdutts7/skills
