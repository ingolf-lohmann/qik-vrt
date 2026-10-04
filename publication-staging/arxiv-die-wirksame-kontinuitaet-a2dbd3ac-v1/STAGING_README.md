# Die wirksame Kontinuität — arXiv staging

Status: PREPARED_REVIEW_REQUIRED_NOT_SUBMITTED

Frozen source: a2dbd3ac25c2935a022ea8ef54d95912e34035f7, tree 377df23cdc2816629332dc5f8e95834ad79687d0, PR #447. main.pdf is a new derived rendering; the original 22-page PDF and original ZIP remain byte-identical at their existing paths.

The minimal arxiv-source.tar.gz contains exactly seven TeX inputs: main.tex, orientation.tex, theory.tex, measurements.tex, delivery.tex, appendix.tex and claim-scope.tex. It contains no PDF, build products, secrets, font binaries, unrelated code or publication authorization. main.tex is the only top-level TeX file; bibliography and source references remain in appendix.tex. Claim boundaries are included in the rendered manuscript and bound separately in CLAIM_MATRIX.json and METHOD_CLAIM_BOUNDARIES.md.

Run `python3 -B publication-staging/arxiv-die-wirksame-kontinuitaet-a2dbd3ac-v1/build.py --check` from the repository root. XeLaTeX and Poppler are the existing declared publication tools. The build extracts only allowlisted regular archive members and uses no shell escape. The deterministic gzip/tar archive is rebuilt and compared; two fresh extractions are compiled independently and compared to main.pdf.

Local TeX Live and dependency versions are reported in BUILD_VALIDATION.json. A clean local build does not prove arXiv server compatibility, moderation, category acceptance, endorsement, account access or a license choice. Candidate metadata is a review proposal; it grants no author decision or submission authority. Follow the separately required exact-artifact and action-time authorization after reviewing this new PDF and archive. Wikipedia is not an arXiv staging prerequisite.
