# QIK-VRT Open Node Request Queue

This folder is intentionally open-ended. Do not predeclare a node count.
Add future Node request rows to OPEN_NODE_REQUESTS.tsv or add additional TSV files with the same columns.
The Seed revalidation workflow reads all queue rows on each run and does not perform global scanning.

Columns:
guid<TAB>source_repo<TAB>seed_repo<TAB>request_url<TAB>node_branch<TAB>heartbeat_ttl_minutes<TAB>lifecycle_policy

Allowed lifecycle_policy values: ACTIVE, SUSPENDED, REVOKED.
