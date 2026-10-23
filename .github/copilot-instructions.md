# QIK-VRT Copilot instructions

Before generating or modifying project content, read the root file `AI`, parse
`AI_CONTEXT.json`, and follow its `required_read_order`.

Repository evidence is authoritative over chat or model memory. Preserve
provenance, effect boundaries, tests, hashes, and the explicit licensing split:
freely available architecture does not automatically license the concrete
implementation as open source. Treat symmetric canonicality as verified only
for byte-equivalent declared scope.

For a repair assignment, reproduce each reported defect against the current raw
source before changing it; classify disproved or unresolved hypotheses explicitly.
Start at bootstrap and actual executor admission, then run the affected regression
tests, `make ai-runtime-contract`, integrity verification and the full `make test`.
Repair concrete failures through the existing components, and return exact
HEAD/TREE-bound evidence in a reviewable pull request. Readiness and receipt
consistency do not authenticate a Principal or prove task execution.

Continue safe, authorized and callable successors under the existing Owner grant.
Preserve platform approval, credential and billing boundaries; an issue assignment
or review request is not proof that a Copilot session started or a repair completed.
