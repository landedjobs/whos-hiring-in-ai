# Contributing

This list is curated from real hiring posts on X. Two ways to help:

## 1. Suggest a post (easiest)

[Open an "Add a hiring post" issue →](https://github.com/landedjobs/whos-hiring-in-ai/issues/new?template=add-hiring-post.yml) with the X link. We review and fold it into the next refresh.

**What belongs here:** genuine hiring posts from founders, hiring managers, or recruiters, AI-adjacent or from AI-native teams. A direct careers link is a bonus but not required — many great roles are "reply / DM me" posts.

**What doesn't:** engagement bait ("drop your portfolio 👇"), résumé-farming threads, job-board reposts, or roles with no AI angle.

## 2. Open a PR

The page is generated — **don't edit `README.md` directly** (it's overwritten on every build). Instead edit the data and regenerate:

1. Add your post object to `data/posts.json` (match the existing shape — `tweetId`, `tweetUrl`, `category`, `postedAt`, `text`, `author`, `stats`, and optional `links`).
2. Run `python3 build.py` to regenerate `README.md`.
3. Commit both files and open a PR.

`category` is one of `job_posting`, `referral_offer`, `hiring_roundup`, `talent_program`. Role sections (AI/ML, GTM, etc.) are classified automatically from the post text — you don't set them.

Thanks for keeping the list fresh. 🙏
