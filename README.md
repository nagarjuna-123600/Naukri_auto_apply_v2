# Naukri Auto Apply Bot V2

Automatically applies to IT jobs and internships on Naukri.com every 4 hours using GitHub Actions.

## Features
- ✅ Cookie-based login (email/password fallback)
- ✅ Daily name alternation (Pulabala Nagarjuna / Nagarjuna Pulabala)
- ✅ Section 0 — New jobs & internships (last 24 hrs)
- ✅ Section 1 — Hyderabad office jobs
- ✅ Section 2 — Hyderabad internships
- ✅ Section 3 — Remote/WFH jobs
- ✅ Section 4 — Remote/WFH internships
- ✅ IT-only strict filter
- ✅ Saves redirect jobs to Naukri Saved Jobs
- ✅ Duplicate prevention

## GitHub Secrets Required
Go to repo → Settings → Secrets and variables → Actions → Add:

| Secret | Value |
|---|---|
| `NAUKRI_EMAIL` | Your Naukri email |
| `NAUKRI_PASSWORD` | Your Naukri password |
| `NAUKRI_COOKIES` | Exported cookies JSON from browser |
| `PAT_TOKEN` | GitHub Personal Access Token |

## Schedule
Runs automatically every 4 hours — 24/7 for free!
