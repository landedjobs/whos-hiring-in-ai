#!/usr/bin/env python3
"""Render README.md from data/posts.json — the curated feed of real hiring posts from X.

data/posts.json: {"updatedAt": "YYYY-MM-DD", "posts": [...]}  (post shape = bookmark-agent output)
Run: python3 build.py
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = "https://landed.jobs"
ORG = "https://github.com/landedjobs"
BRAND = "Landed"
FRESH_DAYS = 14
ARCHIVE_DAYS = 45

CATS = [
	("job_posting", "💼", "Direct job posts", "Founders and hiring managers posting openings on their own timeline — reply fast, these move quickly."),
	("hiring_roundup", "🧵", "Roundups & curators", "Accounts that regularly compile who's hiring. Worth following at the source."),
	("talent_program", "🎓", "Talent programs", "Fellowships, residencies and structured programs announced on X."),
	("referral_offer", "🤝", "Referral offers", "People publicly offering to refer candidates — the warmest way in."),
]


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
	if len(s) <= n:
		return s
	return s[:n].rsplit(" ", 1)[0].rstrip(",.;:-") + " …"


def k(n) -> str:
	n = n or 0
	return f"{n/1000:.1f}".rstrip("0").rstrip(".") + "k" if n >= 1000 else str(n)


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


def row(p, now) -> str:
	a = p["author"]
	h = a["screenName"]
	profile = a.get("profileUrl") or f"https://x.com/{h}"
	who = (
		f'<a href="{profile}"><img src="https://unavatar.io/x/{h}" width="44" alt="@{h}"></a><br>'
		f'<b><a href="{profile}">{esc(a.get("name") or h)}</a></b><br>'
		f'<sub>@{h} · {k(a.get("followers"))} followers</sub>'
	)
	likes = p["stats"].get("likes", 0)
	meta = f'<sub>❤️ {k(likes)} · 🔁 {k(p["stats"].get("retweets", 0))} · {age(p["postedAt"], now)}</sub>'
	post = f"{excerpt(p['text'])}<br>{meta}"
	btns = [
		f'<a href="{p["tweetUrl"]}"><img src="https://img.shields.io/badge/View_post-000000?style=for-the-badge&logo=x&logoColor=white" alt="View post"></a>'
	]
	links = job_links(p)
	if links:
		btns.append(
			f'<a href="{links[0]}"><img src="https://img.shields.io/badge/Apply-ff5b29?style=for-the-badge&logoColor=white" alt="Apply"></a>'
		)
		if len(links) > 1:
			btns.append(f'<sub><a href="{p["tweetUrl"]}">+{len(links) - 1} more roles</a></sub>')
	return f"| {who} | {post} | {'<br>'.join(btns)} |"


def table(posts, now) -> str:
	head = "| Who's hiring | The post | Go |\n|:---:|:---|:---:|"
	return "\n".join([head] + [row(p, now) for p in posts])


def section(emoji, title, sub, posts, now, anchor) -> str:
	if not posts:
		return ""
	live = [p for p in posts if days_old(p, now) <= ARCHIVE_DAYS]
	old = [p for p in posts if days_old(p, now) > ARCHIVE_DAYS]
	out = f'<a name="{anchor}"></a>\n## {emoji} {title} · {len(posts)}\n\n_{sub}_\n\n'
	if live:
		out += table(live, now) + "\n"
	if old:
		out += f"\n<details>\n<summary><b>🗄️ {len(old)} older posts</b> (roles may be filled — still great accounts to follow)</summary>\n\n{table(old, now)}\n\n</details>\n"
	return out + "\n[⬆ back to top](#top)\n"


def main():
	updated, posts = load()
	now = datetime.now(timezone.utc)
	today = updated or now.strftime("%Y-%m-%d")
	by_cat = {c: [p for p in posts if p["category"] == c] for c, *_ in CATS}
	fresh = [p for p in posts if days_old(p, now) <= FRESH_DAYS][:12]
	authors = len({p["author"]["screenName"] for p in posts})

	toc = "\n".join(
		f"- [{emoji} {title}](#{cat}) · **{len(by_cat[cat])}**" for cat, emoji, title, _ in CATS if by_cat[cat]
	)
	fresh_block = (
		f'<a name="fresh"></a>\n## 🔥 Freshest {len(fresh)}\n\n'
		f"_The newest posts across every category. Reply-speed matters on X — start here._\n\n{table(fresh, now)}\n\n[⬆ back to top](#top)\n\n---\n\n"
		if fresh
		else ""
	)
	sections = "\n---\n\n".join(
		s for cat, emoji, title, sub in CATS if (s := section(emoji, title, sub, by_cat[cat], now, cat))
	)

	readme = f"""<a name="top"></a>

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
  <img src="assets/banner-light.svg" alt="Who's Hiring in AI — real hiring posts from X" width="100%">
</picture>

![Posts](https://img.shields.io/badge/{len(posts)}%20hiring%20posts-ff5b29?style=flat-square) ![Sources](https://img.shields.io/badge/{authors}%20hiring%20accounts-6C2BD9?style=flat-square) ![Updated](https://img.shields.io/badge/updated-{today.replace('-', '.')}-00A86B?style=flat-square) [![Stars](https://img.shields.io/github/stars/landedjobs/whos-hiring-in-ai?style=social)](https://github.com/landedjobs/whos-hiring-in-ai)

**Real hiring posts by real people — founders, hiring managers and recruiters posting on X.**
Jobs surface here *before* they hit job boards, and a reply or DM beats a cold application every time.

*Hand-curated, refreshed every few days by [{BRAND}]({SITE}).*

[🔥 Fresh](#fresh) · {' · '.join(f'[{emoji} {title}](#{cat})' for cat, emoji, title, _ in CATS if by_cat[cat])}

</div>

---

> **Why this exists** — the best AI jobs increasingly get filled from a single post on X: the founder posts, fifty people reply, someone gets hired, and the role never reaches LinkedIn. We bookmark these posts as we scout roles for [{BRAND}]({SITE}) users and publish the curation here. ⭐ **Star this repo** — it refreshes every 2–3 days.

## Jump to

{toc}

---

{fresh_block}{sections}

---

## How this list is built

An agent reads our team's curated X bookmarks every 2–3 days, keeps only genuine hiring posts (no engagement bait, no "drop your portfolio" farming), classifies them, and rebuilds this page. Older posts move into the collapsible archive — the accounts stay worth following even after a role is filled.

**Spotted a great hiring post?** [Open an issue]({ORG}/whos-hiring-in-ai/issues) with the link and we'll fold it in.

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
	print(f"README.md: {len(posts)} posts, {len(fresh)} fresh, {authors} authors")


if __name__ == "__main__":
	main()
