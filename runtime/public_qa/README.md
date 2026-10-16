# QIK-VRT public question service — bounded preview

This service is an optional, fail-closed backend for the public question entrypoint
\`docs/fragen/index.html\`. It does **not** independently verify scientific claims,
perform arbitrary web research, publish articles, run the universal transputer, or
issue an external \`EFFECT_ACK_DONE\`.

## Run and verify locally

\`\`\`sh
python3 -m unittest tests.test_public_qa_server tests.test_public_question_entrypoint -v
PORT=8080 python3 -m runtime.public_qa.server
curl -fsS http://127.0.0.1:8080/api/health
curl -fsS -H 'Origin: http://localhost:8080' -H 'Content-Type: application/json' \
  --data '{"question":"Was ist QIK-VRT?"}' http://127.0.0.1:8080/api/ask
\`\`\`

Without inference credentials, a relevant question returns \`EVIDENCE_ONLY\` with
locally shipped, hashed repository excerpts. Unrelated questions return
\`NOT_ENOUGH_EVIDENCE\`. The browser transparently falls back to the existing
local rule console if \`/api/ask\` is unavailable.

## Deployment configuration (separate acceptance required)

Dockerfile: \`runtime/public_qa/Dockerfile\` with **repository root** as build context.

- \`PORT\`: default 8080.
- \`QIKVRT_ALLOWED_ORIGINS\`: exact comma-separated origins, no wildcards.
  Set the actual verified HTTPS origin(s) on the deployment.
- \`QIKVRT_SOURCE_COMMIT\`: 40-character immutable SHA for the source files
  packaged in the deployed image. An absent/invalid value yields
  \`MUTABLE_MAIN\` source labels and **disables model inference**.
- \`QIKVRT_QA_ENABLED=true\`: required explicit opt-in to model inference.
  Default false.
- \`QIKVRT_QA_PROVIDER\`: \`anthropic\` or \`openai\`.
- \`QIKVRT_QA_MODEL\`: explicitly selected provider model.
- \`QIKVRT_ANTHROPIC_API_KEY\` or \`QIKVRT_OPENAI_API_KEY\`: secret only in
  provider-managed runtime variables. Never commit a key.

The only outbound inference destinations are the provider's pinned HTTPS API
hosts. Sources are a fixed, local, allowlisted repository subset; no arbitrary
URLs, scraping, GitHub writes, external publication or arbitrary tools.
Questions are not written to persistent storage by this application, but
a configured external model provider receives the submitted question and
excerpts. Its privacy terms must be reviewed before public activation.

This is **not yet** a general-purpose answer service. Public rollout also
requires independent review, exact-head CI, secure inference credentials,
abuse/privacy assessment, accepted deployment, correct DNS/TLS, an independent
live answer/no-answer test, and exact public byte readback. Railway staging or
a successful build alone cannot satisfy those effects. The existing
\`ingolf-lohmann/qik-vrt\` Authority and \`Goldkelch/qik-vrt\` Mirror roles
are unchanged.
