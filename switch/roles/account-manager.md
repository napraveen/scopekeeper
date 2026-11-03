Account Manager governance responsibility (held by Priya in config/rooms.yaml).

Authorized commands in acme-delivery and acme-cr-NNN rooms:
- `@clerk approve` or `@clerk approve A,C,D` — Approves all or selected change-order options to send to the client.
- `@clerk price <A|B|C|D> <usd_amount>` — Overrides one option's price before approval (logged in the ledger).
- `@clerk goodwill <ASK-NNNN>` — Marks a small ask (< 2h) as complimentary from the monthly goodwill bucket.
- `@clerk decline <CR-NNN> <reason>` — Declines a change request and instructs Scout to notify the client politely.
