# Redis Key Schema

Placeholder — populated in Milestone 2 when the Celery polling pipeline is implemented.

## Planned key namespaces

| Key pattern | Type | TTL | Purpose |
|-------------|------|-----|---------|
| `sniper:poll:open:{semester_code}` | Set | 120s | Currently-open index numbers (global, replaces watcher.py `currently_open`) |
| `sniper:poll:lock:{semester_code}` | String | 30s | Distributed lock preventing concurrent poll tasks |
| `sniper:course:cache:{semester_code}` | Hash | 700s | index_number → serialized CourseDetail JSON (replaces enricher.py cache) |

## Design notes

- Redis is the **real-time deduplication layer** for notifications (M2).
- `index_state` table is the **durable audit layer** — it survives Redis flush.
- Notification deduplication gate: `SISMEMBER sniper:poll:open:{sem} {index}` before dispatch.
