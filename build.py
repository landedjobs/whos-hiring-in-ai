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
	# unavatar pulls the real X avatar; ui-avatars fallback guarantees an image so no broken tiles.
	initial = (name or h or "?").strip()[:1].upper() or "?"
	fb = f"https://ui-avatars.com/api/?name={quote(initial)}&size=64&background=6C2BD9&color=fff&bold=true&format=png"
	return f"https://unavatar.io/x/{h}?fallback={quote(fb, safe='')}"


def btn(url: str, label: str, color: str, logo: str | None = None) -> str:
	# height=34 + non-black colors so buttons are clearly visible on GitHub dark theme.
	logo_part = f"&logo={logo}&logoColor=white" if logo else ""
	return f'<a href="{url}"><img src="https://img.shields.io/badge/{label}-{color}?style=for-the-badge{logo_part}" height="34" alt="{label}"></a>'


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
		go = btn(links[0], "Apply", "ff5b29") + "<br>" + btn(p["tweetUrl"], "𝕏_Post", "1DA1F2", "x")
		if len(links) > 1:
			go += f'<br><sub><a href="{p["tweetUrl"]}">+{len(links) - 1} more roles</a></sub>'
	else:
		# No external link → the play is to reply / DM on the post itself.
		go = btn(p["tweetUrl"], "Open_on_𝕏", "6C2BD9", "x")
	return f"| {who} | {post} | {go} |"


def table(posts, now) -> str:
	head = "| Who's hiring | The post | Go |\n|:---:|:---|:---:|"
	return "\n".join([head] + [row(p, now) for p in posts])


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

	role_links = [f"[{ROLE_META[key][0]} {ROLE_META[key][1]}](#{key})" for key in ROLE_ORDER if by_role[key]]
	cat_links = [f"[{e} {t}](#{c})" for c, e, t, _ in GROUPS if by_cat[c]]
	nav = " · ".join(["[🔥 Fresh](#fresh)"] + role_links + cat_links)

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

	readme = f"""<a name="top"></a>

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
  <img src="assets/banner-light.svg" alt="Who's Hiring in AI — real hiring posts from X" width="100%">
</picture>

![Posts](https://img.shields.io/badge/{len(posts)}%20hiring%20posts-ff5b29?style=flat-square) ![Sources](https://img.shields.io/badge/{authors}%20hiring%20accounts-6C2BD9?style=flat-square) ![Updated](https://img.shields.io/badge/updated-{today.replace('-', '.')}-00A86B?style=flat-square) [![Stars](https://img.shields.io/github/stars/landedjobs/whos-hiring-in-ai?style=social)](https://github.com/landedjobs/whos-hiring-in-ai)

**Real hiring posts by real people — founders, hiring managers and recruiters posting on X**, sorted by role.
Jobs surface here *before* they hit the job boards, and a reply or DM beats a cold application every time.

*Hand-curated, refreshed every few days by [{BRAND}]({SITE}).*

{nav}

</div>

---

> **Why this exists** — the best AI jobs increasingly get filled from a single post on X: the founder posts, fifty people reply, someone gets hired, and the role never reaches LinkedIn. We bookmark these as we scout roles for [{BRAND}]({SITE}) users and publish the curation here, sorted by role. ⭐ **Star this repo** — it refreshes every 2–3 days.

## Jump to

{toc}

> ➕ **Know a hiring post we're missing?** [Add it in 30 seconds →]({ORG}/whos-hiring-in-ai/issues/new?template=add-hiring-post.yml) · see [CONTRIBUTING](CONTRIBUTING.md)

---

{body}

---

## How this list is built

An agent reads our team's curated X bookmarks every 2–3 days, keeps only genuine hiring posts (no engagement bait, no "drop your portfolio" farming), sorts them by role, and rebuilds this page. Older posts fall into each section's collapsible archive — the accounts stay worth following even after a role is filled.

**Want in?** [Submit a hiring post]({ORG}/whos-hiring-in-ai/issues/new?template=add-hiring-post.yml) or open a PR editing `data/posts.json`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## How to actually convert these into interviews

Replying "interested!" alongside 200 other people is still spraying. What works: a same-day reply with one concrete, relevant thing you've built, then a short DM referencing the post. Fewer, better applications beat the spray — [{BRAND}]({SITE}) brings you matched roles daily, drafts your answers to each application's questions, and preps you with courses and voice mock interviews.

**[Get started free → {SITE}]({SITE})**

## Related

- 🧭 [awesome-ai-native-jobs]({ORG}/awesome-ai-native-jobs) — the umbrella for the whole family
- 🚀 [ai-engineer-jobs]({ORG}/ai-engineer-jobs) — 300 live AI engineer roles, auto-updated
- 💸 [recently-funded-ai-startups-hiring]({ORG}/recently-funded-ai-startups-hiring) — fresh-capital companies that are hiring

<div align="center">
<sub>{len(posts)} posts from {authors} accounts · updated {today} · maintained by <a href="{SITE}">{BRAND}</a>. All posts belong to their authors — we link, we don't copy. Not affiliated with X.</sub>
</div>
"""
	(HERE / "README.md").write_text(readme, encoding="utf-8")
	dist = ", ".join(f"{ROLE_META[key][1]}:{len(by_role[key])}" for key in ROLE_ORDER if by_role[key])
	print(f"README.md: {len(posts)} posts, {authors} authors · roles → {dist}")


if __name__ == "__main__":
	main()
