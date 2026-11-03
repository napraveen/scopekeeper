Delivery Lead governance responsibility (held by Ravi in config/rooms.yaml).

Authorized commands in acme-delivery and acme-cr-NNN rooms:
- `@clerk confirm` — Confirms the Estimator's P50 hours estimate for the change request.
- `@clerk hours <number>` — Sets confirmed hours for the full estimate and triggers Clerk's pricing and date-impact calculation.
- `@clerk hours smaller <number>` — Confirms or adjusts the hours for the smaller scope option.
