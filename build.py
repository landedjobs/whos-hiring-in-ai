#!/usr/bin/env python3
"""Render README.md from data/posts.json — the curated feed of real hiring posts from X.

data/posts.json: {"updatedAt": "YYYY-MM-DD", "posts": [...]}  (post shape = bookmark-agent output)
Run: python3 build.py
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

HERE = Path(__file__).resolve().parent
SITE = "https://landed.jobs"
ORG = "https://github.com/landedjobs"
BRAND = "Landed"
CDN = "https://static.b100x.ai/github-repos/images"  # banners, buttons, avatars — served from our bucket
SLUG = "whos-hiring-in-ai"
FRESH_DAYS = 14
ARCHIVE_DAYS = 45

# Role buckets, in priority order (a post is filed under its first strong match).
ROLES = [
	("ai-ml", "🤖", "AI / ML / Research", r"\b(ai[ /-]?eng|ml[ /-]?eng|machine learning|applied scientist|research (?:engineer|scientist)|\bllm\b|deep learning|\bnlp\b|computer vision|ai researcher|generative ai|agent(?:ic|s)? (?:engineer|team|platform)|founding (?:ai|ml)|ai/ml|prompt engineer)\b"),
	("data", "📊", "Data", r"\b(data engineer|data scientist|data analyst|analytics engineer|data science|analytics)\b"),
	("fde", "🤝", "Forward-deployed & Solutions", r"\b(forward[ -]?deployed|\bfde\b|solutions? engineer|solutions? architect|field engineer|customer engineer|deployment (?:engineer|strateg))\b"),
	("swe", "💻", "Software & Infra", r"\b(software engineer|\bswe\b|full[ -]?stack|back[ -]?end|front[ -]?end|devops|infrastructure|\binfra\b|platform engineer|production engineer|network engineer|systems? engineer|smart contract|solidity|web3|mobile engineer|\bios\b|android|security engineer|founding engineer|first engineer)\b"),
	("gtm", "🚀", "GTM & Growth", r"\b(gtm|go[ -]?to[ -]?market|growth (?:engineer|lead|marketer|hacker)|\bsales\b|account executive|\bae\b|business development|\bbd\b|outbound|revenue|marketing|demand gen|partnerships)\b"),
	("product", "🎨", "Product & Design", r"\b(product manage(?:r|ment)|\bpm\b|product lead|head of product|director of product|product owner|product engineer|designer|design(?:ers)?|\bux\b|\bui\b|product design|motion design|brand design)\b"),
]
COMPANYWIDE = re.compile(r"\b(across the (?:company|team|board|org)|company[- ]wide|\d{2,}\+? (?:open )?roles|many roles|multiple roles|several roles|hiring for (?:a lot|lots|tons))\b", re.I)
OTHER = ("other", "🧩", "Other roles")
ROLE_ORDER = [r[0] for r in ROLES] + ["company", "other"]
ROLE_META = {r[0]: (r[1], r[2]) for r in ROLES} | {"company": ("🏢", "Multiple / company-wide"), "other": OTHER[1:]}

# Non-role sections rendered after the role buckets.
GROUPS = [
	("hiring_roundup", "🧵", "Roundups & curators", "Accounts that regularly compile who's hiring — worth following at the source."),
	("talent_program", "🎓", "Fellowships & programs", "Fellowships, residencies and structured programs announced on X."),
]


def classify(p) -> str:
	override = (p.get("bucket") or "").strip()
	if override in ROLE_ORDER:  # human-verified bucket wins over the regex
		return override
	text = p.get("text", "") or ""
	matches = [key for key, _, _, pat in ROLES if re.search(pat, text, re.I)]
	if COMPANYWIDE.search(text) or len(matches) >= 3:
		return "company"
	if matches:
		return matches[0]
	# Fallback: a bare "engineer(s)" with no role qualifier → software.
	return "swe" if re.search(r"\bengineers?\b", text, re.I) else "other"


def load():
	d = json.loads((HERE / "data" / "posts.json").read_text(encoding="utf-8"))
	posts = sorted(d["posts"], key=lambda p: p["postedAt"], reverse=True)
	seen, out = set(), []
	for p in posts:
		if p["tweetId"] not in seen:
			seen.add(p["tweetId"])
			out.append(p)
	return d.get("updatedAt"), out


def esc(s: str) -> str:
	s = re.sub(r"https?://\S+", "", s or "")
	s = re.sub(r"\s+", " ", s).strip()
	return s.replace("|", "&#124;").replace("<", "&lt;").replace(">", "&gt;")


def excerpt(s: str, n: int = 210) -> str:
	s = esc(s)
	return s if len(s) <= n else s[:n].rsplit(" ", 1)[0].rstrip(",.;:-") + " …"


def k(n) -> str:
	n = n or 0
	return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k" if n >= 1000 else str(n)


def age(iso: str, now: datetime) -> str:
	d = (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
	if d <= 0:
		return "today"
	if d < 30:
		return f"{d}d ago"
	if d < 365:
		return f"{d // 30}mo ago"
	return f"{d // 365}y ago"


def days_old(p, now):
	return (now - datetime.fromisoformat(p["postedAt"].replace("Z", "+00:00"))).days


def job_links(p):
	raw = " ".join(p.get("links") or [])
	return [u for u in re.split(r"\s+", raw) if u.startswith("http")]


def avatar(h: str, name: str) -> str:
	# mirrored to our bucket by _shared/mirror_avatars.py (real X avatar, or branded letter fallback)
	return f"{CDN}/avatars/x/{h}.png"


def btn(url: str, name: str, alt: str) -> str:
	return f'<a href="{url}"><img src="{CDN}/buttons/{name}.svg" width="71" alt="{alt}"></a>'


def row(p, now) -> str:
	a = p["author"]
	h = a["screenName"]
	profile = a.get("profileUrl") or f"https://x.com/{h}"
	who = (
		f'<a href="{profile}"><img src="{avatar(h, a.get("name"))}" width="48" height="48" alt="@{h}"></a><br>'
		f'<b><a href="{profile}">{esc(a.get("name") or h)}</a></b><br>'
		f'<sub>@{h} · {k(a.get("followers"))} followers</sub>'
	)
	meta = f'<sub>❤️ {k(p["stats"].get("likes", 0))} · 🔁 {k(p["stats"].get("retweets", 0))} · {age(p["postedAt"], now)}</sub>'
	post = f"{excerpt(p['text'])}<br>{meta}"
	links = job_links(p)
	if links:
		go = btn(links[0], "apply", "Apply") + "<br>" + btn(p["tweetUrl"], "view-post", "View post")
		if len(links) > 1:
			go += f'<br><sub><a href="{p["tweetUrl"]}">+{len(links) - 1} more roles</a></sub>'
	else:
		# No external link → the play is to reply / DM on the post itself.
		go = btn(p["tweetUrl"], "open-x", "Open on X")
	return f'<tr><td align="center" width="150">{who}</td><td>{post}</td><td align="center" width="95">{go}</td></tr>'


def table(posts, now) -> str:
	# Raw HTML table: markdown tables can't set td width, and without a fixed Go column
	# GitHub's forced img{max-width:100%} lets the text column crush the buttons to nothing.
	head = '<tr><th align="center">Who&#39;s hiring</th><th align="left">The post</th><th align="center">Go</th></tr>'
	return "<table>\n" + "\n".join([head] + [row(p, now) for p in posts]) + "\n</table>"


def section(anchor, emoji, title, sub, posts, now) -> str:
	if not posts:
		return ""
	live = [p for p in posts if days_old(p, now) <= ARCHIVE_DAYS]
	old = [p for p in posts if days_old(p, now) > ARCHIVE_DAYS]
	out = f'<a name="{anchor}"></a>\n## {emoji} {title} · {len(posts)}\n\n_{sub}_\n\n'
	if live:
		out += table(live, now) + "\n"
	if old:
		out += f"\n<details>\n<summary><b>🗄️ {len(old)} older {title.lower()} posts</b> (roles may be filled — the accounts stay worth following)</summary>\n\n{table(old, now)}\n\n</details>\n"
	return out + "\n[⬆ back to top](#top)\n"


ROLE_SUB = {
	"ai-ml": "AI, ML, research and agent-engineering roles.",
	"data": "Data engineering, data science and analytics roles.",
	"fde": "Forward-deployed, solutions and customer-facing engineering.",
	"swe": "Software, infrastructure and platform roles.",
	"gtm": "Go-to-market, sales, growth and marketing roles.",
	"product": "Product management and design roles.",
	"company": "Founders hiring across the whole company — many roles in one post.",
	"other": "Ops, chief-of-staff, content and everything else.",
}


def main():
	updated, posts = load()
	now = datetime.now(timezone.utc)
	today = updated or now.strftime("%Y-%m-%d")
	authors = len({p["author"]["screenName"] for p in posts})

	# Role buckets draw from direct job posts + referral offers; roundups/programs stay separate.
	role_pool = [p for p in posts if p["category"] in ("job_posting", "referral_offer")]
	by_role = {key: [] for key in ROLE_ORDER}
	for p in role_pool:
		by_role[classify(p)].append(p)
	by_cat = {c: [p for p in posts if p["category"] == c] for c, *_ in GROUPS}

	fresh = [p for p in posts if days_old(p, now) <= FRESH_DAYS][:12]

	toc = "\n".join(
		[f"- [🔥 Freshest {len(fresh)}](#fresh)"]
		+ [f"- [{ROLE_META[key][0]} {ROLE_META[key][1]}](#{key}) · **{len(by_role[key])}**" for key in ROLE_ORDER if by_role[key]]
		+ [f"- [{e} {t}](#{c}) · **{len(by_cat[c])}**" for c, e, t, _ in GROUPS if by_cat[c]]
	)

	fresh_block = (
		f'<a name="fresh"></a>\n## 🔥 Freshest {len(fresh)}\n\n'
		f"_The newest posts across every role. Reply-speed matters on X — start here._\n\n{table(fresh, now)}\n\n[⬆ back to top](#top)\n\n---\n\n"
		if fresh
		else ""
	)
	role_sections = "\n---\n\n".join(
		s for key in ROLE_ORDER if (s := section(key, ROLE_META[key][0], ROLE_META[key][1], ROLE_SUB[key], by_role[key], now))
	)
	cat_sections = "\n---\n\n".join(
		s for c, e, t, sub in GROUPS if (s := section(c, e, t, sub, by_cat[c], now))
	)
	body = "\n\n---\n\n".join(b for b in [fresh_block.rstrip("\n- \n"), role_sections, cat_sections] if b)

	related = "\n".join([
		f"- 🧭 [awesome-ai-native-jobs]({ORG}/awesome-ai-native-jobs) — the umbrella that maps the whole AI-native job landscape",
		f"- 💸 [recently-funded-ai-startups-hiring]({ORG}/recently-funded-ai-startups-hiring) — fresh-capital startups staffing up now",
		f"- 🚀 [ai-engineer-jobs]({ORG}/ai-engineer-jobs) — 300 live AI engineer roles, auto-updated",
		f"- 🧠 [llm-engineer-jobs]({ORG}/llm-engineer-jobs) — LLM engineering roles",
		f"- 🤖 [ai-agent-engineer-jobs]({ORG}/ai-agent-engineer-jobs) — agent-building roles",
		f"- 🤝 [forward-deployed-engineer-jobs]({ORG}/forward-deployed-engineer-jobs) — FDE & customer-facing engineering",
		f"- 📈 [gtm-engineer-jobs]({ORG}/gtm-engineer-jobs) — GTM engineering roles",
		f"- 🎓 [ai-fellowships-and-residencies]({ORG}/ai-fellowships-and-residencies) — 75 fellowships, residencies & programs",
		f"- 📘 [ai-interview-guides]({ORG}/ai-interview-guides) — 33 company interview guides",
		f"- ❓ [ai-interview-questions]({ORG}/ai-interview-questions) — 331 real interview questions with answers",
		f"- 🧪 [projects-to-land-an-ai-job]({ORG}/projects-to-land-an-ai-job) — portfolio projects that actually get you hired",
		f"- 🗺️ [ai-product-engineer-roadmap]({ORG}/ai-product-engineer-roadmap) — the AI product engineer roadmap",
	])

	readme = f"""<a name="top"></a>

<div align="center">

<a href="{SITE}"><img src="https://static.b100x.ai/email/landed-wordmark.png" alt="Landed" width="200"></a>

<img src="{CDN}/{SLUG}/banner.svg" alt="Who's Hiring in AI" width="100%">

![Posts](https://img.shields.io/badge/{len(posts)}%20hiring%20posts-ff5b29?style=flat-square) ![Sources](https://img.shields.io/badge/{authors}%20hiring%20accounts-6C2BD9?style=flat-square) ![Updated](https://img.shields.io/badge/updated-{today.replace('-', '.')}-00A86B?style=flat-square) [![Stars](https://img.shields.io/github/stars/landedjobs/whos-hiring-in-ai?style=social)](https://github.com/landedjobs/whos-hiring-in-ai)

**Real hiring posts by real people — founders, hiring managers and recruiters posting on X**, sorted by role.
Jobs surface here *before* they hit the job boards, and a reply or DM beats a cold application every time.

*Hand-curated, refreshed every few days by [{BRAND}]({SITE}).*

</div>

---

> **Why this exists** — the best AI jobs increasingly get filled from a single post on X: the founder posts, fifty people reply, someone gets hired, and the role never reaches LinkedIn. We bookmark these as we scout roles for [{BRAND}]({SITE}) users and publish the curation here, sorted by role. ⭐ **Star this repo** — it refreshes every 2–3 days.

## Jump to

{toc}

> ➕ **Know a hiring post we're missing?** [Add it in 30 seconds →]({ORG}/whos-hiring-in-ai/issues/new?template=add-hiring-post.yml) · see [CONTRIBUTING](CONTRIBUTING.md)

---

{body}

---

## How to actually convert these into interviews

Replying "interested!" alongside 200 other people is still spraying. What works: a same-day reply with one concrete, relevant thing you've built, then a short DM referencing the post. Fewer, better applications beat the spray — [{BRAND}]({SITE}) brings you matched roles daily, drafts your answers to each application's questions, and preps you with courses and voice mock interviews.

**[Get started free → {SITE}]({SITE})**

---

## How this list is built

An agent reads our team's curated X bookmarks every 2–3 days, keeps only genuine hiring posts (no engagement bait, no "drop your portfolio" farming), sorts them by role, and rebuilds this page. Older posts fall into each section's collapsible archive — the accounts stay worth following even after a role is filled.

**Want in?** [Submit a hiring post]({ORG}/whos-hiring-in-ai/issues/new?template=add-hiring-post.yml) or open a PR editing `data/posts.json`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Related

Part of the [Landed]({SITE}) AI-native job-search family:

{related}

<div align="center">
<sub>{len(posts)} posts from {authors} accounts · updated {today} · maintained by <a href="{SITE}">{BRAND}</a>. All posts belong to their authors — we link, we don't copy. Not affiliated with X.</sub>
</div>
"""
	(HERE / "README.md").write_text(readme, encoding="utf-8")
	dist = ", ".join(f"{ROLE_META[key][1]}:{len(by_role[key])}" for key in ROLE_ORDER if by_role[key])
	print(f"README.md: {len(posts)} posts, {authors} authors · roles → {dist}")


if __name__ == "__main__":
	main()
