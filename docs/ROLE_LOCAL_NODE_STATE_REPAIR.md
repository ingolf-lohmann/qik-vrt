# Role-local Mirror node-state repair

This repair restores the active Mirror node's parser-compatible liveness triple after whole-tree Authority/Mirror convergence removed role-local mutable state from Mirror `main`.

The causal invariant is not perpetual whole-tree equality. It is preservation of shared canonical structure together with every role-local difference required for identity, liveness, authority, or function.

`Shared(Authority) = Shared(Mirror)` may coexist with `Local(Authority) != Local(Mirror)`.

The immediate repair restores `NODE_HEALTH.json`, `SEED_ACCEPTANCE_STATUS.json`, and `NODE_REGISTRATION_RENEWAL.json` for node `a84f157a-cef2-4c47-bca9-8f407085bdbe`, bound to Mirror `main` and the freshly reobserved Authority head. It does not change registry identity, Seed exit semantics, Authority `main`, or published history.

The immediate heartbeat is deliberately not presented as a permanent solution. A durable successor must renew the role-local state before the 1,500-minute TTL expires or move mutable node-state to a dedicated role-local state ref with coordinated registry semantics.
