# ChatGPT Library → QIK-VRT: Migration and Evidence Gates

Status: **PREPARED / NOT TRANSFERRED**  
Date: 2026-11-05  
Target: `ingolf-lohmann/qik-vrt` (**public**, verified via GitHub repository metadata).  
Authority main is not modified by this branch.

## Scope and protection

The owner requested durable preservation of the full ChatGPT Library in GitHub. The available GitHub connector exposes only the public QIK-VRT repository. The library includes research materials, executable packages, private correspondence and other potentially sensitive files. Consequently, a blanket upload to this public repository is **not authorized by evidence of appropriate per-file disclosure classification**, even though transfer was requested.

**No file is considered migrated by the existence of this document.**

## Required per-artifact transfer record

For each original source version record:

- library identifier, exact original name/path and version;
- byte length and SHA-256 of original bytes (not merely a 64-character field);
- classification PUBLIC_RELEASE_APPROVED / PRIVATE / RESTRICTED / REVIEW_REQUIRED;
- destination Git repository, exact ref, commit and immutable blob or Git LFS object pointer, or protected external object store locator;
- size and SHA-256 of independent destination readback;
- result EQUAL / MISMATCH / UNREADABLE and timestamp;
- effect acknowledgement/receipt bound to principal, action, destination and artifact (if an admitted EAP path actually exists).

Avoid storing confidential names, file identifiers, contents, credentials or unredacted inventory in this public document.

## Acceptance gates

1. **SOURCE_INVENTORIED**: complete paginated listing, including all folders and versions within declared scope.
2. **SOURCE_BYTES_VERIFIED**: original source bytes actually retrievable and individually hashed.
3. **DESTINATION_AUTHORIZED**: destination access control and disclosure class checked per artifact.
4. **UPLOAD_COMPLETED**: each artifact sent without semantic transformation, including large file handling (prefer protected object storage or Git LFS for binaries; never assume ordinary Git is appropriate for all files).
5. **DESTINATION_READBACK_VERIFIED**: re-fetch actual bytes and compare SHA-256, size and identity.
6. **EFFECT_ACK_VERIFIED**: only claim EAP completion after native authenticated receipt plus independent state readback.
7. **SOURCE_CLEANUP_ALLOWED**: only after all required checks and a separate explicit owner authorization for library deletions.

All gates default to OPEN. A successful GitHub API response is not a readback and a branch commit is not a merge, runtime deployment or EAP DONE.

## Initial observation

A read-only Library listing returned an initial page of 100 entries and a non-null next cursor; **complete enumeration is not yet established**. The accessible destination repository is public and the authenticated GitHub account has push access. No private GitHub repository was found in the owner's accessible repository list. The full collection **has not been copied**.

## Next smallest safe native step

Provide or admit a **private, suitably access-controlled destination** for PRIVATE / RESTRICTED assets (or an appropriate encrypted GitHub-backed archive), then continue full Library pagination and per-file transfer with independent readbacks. Publish only independently classified public artifacts in this public authority repository. Treat already published Zenodo records and repository originals as references, not unnecessary duplicate binaries.

This document records a migration control policy, **not** successful archive migration, memory reclamation or productive EAP.
