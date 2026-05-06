"""Pipeline stage modules for automated_pipeline.py orchestrator.

Each module owns one distinct responsibility:
- scrape    : fetch raw events from external sources
- classify  : SVM inference + confidence/review flagging
- enrich    : enrichment, filtering, image assignment
- notify    : email generation and delivery
- export    : file-based export (CSV, JSON, iCal)
- upload    : WordPress REST API upload
"""
