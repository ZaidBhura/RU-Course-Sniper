# Redis Key Schema

Implemented in Milestone 2 (Async Polling Pipeline).

## Key namespaces

| Key pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `sniper:poll:lock:{semester_code}` | String | 30s | Distributed lock (SETNX/EX) — prevents concurrent poll tasks |
| `sniper:poll:open:{semester_code}` | Set | 120s | Currently-open index numbers (global, replaces watcher.py `currently_open`) |
| `sniper:course:cache:{semester_code}` | Hash | 700s | index_number → serialized CourseDetail JSON (replaces enricher.py in-memory dict) |
| `sniper:notified:{user_id}:{index_number}:{semester_code}` | String | none | Dedup gate — SET after notification sent, DEL on close_reset so re-notification fires |

## Design notes

- Redis is the **real-time layer**: deduplication, lock, and open-section state.
- `index_state` table is the **durable audit layer** — survives Redis flush or restart.
- Notification dedup gate is user-scoped (`{user_id}` prefix) — no cross-tenant bleed.
- Dedup key has no TTL: it is explicitly deleted by `poll_soc` on `close_reset` events,
  mirroring `notified_this_session.discard()` in legacy/watcher.py:129.
- `sniper:poll:open:{semester_code}` TTL (120s) is intentionally longer than poll interval (20s)
  so the set survives a single missed poll cycle without falsely detecting all indexes as closed.
- Course cache TTL (700s) is ENRICH_INTERVAL_SECONDS (600s) + 100s buffer to stay warm
  during a delayed or retrying refresh task.
