"""FreightSight ingest worker.

Runs on a schedule (GitHub Actions, */15) *outside* the web service: it fetches
the slow external feeds, stashes them in Postgres, recomputes the derived
analytics and appends the persistent history the API and the live back-test
read from. See ``worker/ingest.py`` and ``docs/GLOBAL_LIVE_MONITORING.md``.
"""
