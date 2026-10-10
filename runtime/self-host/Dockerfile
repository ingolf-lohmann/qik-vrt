# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# New S1 provisioning/test adapter; historical deployment originals stay intact.
# No provider checkout, gh, credentials or account setup in the runtime image.
FROM node:24-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6 AS node-runtime
FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3 AS runtime
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends \
      firefox-esr libstdc++6 novnc websockify x11-utils x11vnc xvfb ca-certificates \
    && dpkg-query -W -f='${Package}\t${Version}\n' > /usr/local/share/qikvrt-distribution-packages.tsv \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
# This is a provisioned dependency image. Operators transfer a separately
# frozen package and private config/volume; no mutable checkout at runtime.
WORKDIR /source
FROM runtime AS test
RUN apt-get update && apt-get install -y --no-install-recommends git make \
    && git config --system --add safe.directory /source \
    && rm -rf /var/lib/apt/lists/*
