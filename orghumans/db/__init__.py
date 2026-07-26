"""DB package for OrgHumans local SQLite stores.

Each module owns one database file:
  - identity_db.py   → identity.db   (org meta, brand, glossary, github repos)
  - members_db.py    → members.db    (member roster + roles)
  - integrations_db.py → integrations.db (tokens, permissions)
  - sync_log_db.py   → sync_log.db   (offline diff queue)
"""
