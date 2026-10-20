# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# New S1 provisioning/test adapter; historical deployment originals stay intact.
# No provider checkout, gh, credentials or account setup in the runtime image.
ARG SOURCE_DATE_EPOCH
ARG RUNTIME_CARRIER=runtime
ARG QIKVRT_PRODUCTION_IMAGE=runtime
ARG QIKVRT_DEPENDENCY_IMAGE=runtime
ARG QIKVRT_S1_BASE_IMAGE=qikvrt-s1:firefox-158-baseline
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
FROM ${QIKVRT_S1_BASE_IMAGE} AS s1-firefox-release
# The caller verifies the already tested PR457 image before this bounded layer.
# No compiler, native services, repository checkout or noVNC rebuild.
USER root
COPY tools/qikvrt_self_host.py /opt/qikvrt-firefox-upgrade/qikvrt_self_host.py
RUN python3 -B /opt/qikvrt-firefox-upgrade/qikvrt_self_host.py firefox-release-provision \
      --output /opt/qikvrt/runtime/firefox-release
COPY deploy/universal-terminal/entrypoint.sh /usr/local/bin/qikvrt-universal-terminal
RUN chmod 0755 /usr/local/bin/qikvrt-universal-terminal
ENV QIKVRT_FIREFOX_BINARY=/usr/lib/firefox/firefox
USER 10001:10001
FROM ${QIKVRT_DEPENDENCY_IMAGE} AS delivery-runtime
FROM delivery-runtime AS test
USER root
RUN apt-get update && apt-get install -y --no-install-recommends git make \
    && git config --system --add safe.directory /source \
    && rm -rf /var/lib/apt/lists/*

# Upgrade only the original frozen dependency layers with the existing guarded
# Mozilla APT Release adapter; freeze this result once for both OCI builds.
FROM ${RUNTIME_CARRIER} AS production-firefox-runtime
USER root
ARG QIKVRT_SOURCE_HEAD
ARG QIKVRT_SOURCE_TREE
LABEL org.opencontainers.image.revision="$QIKVRT_SOURCE_HEAD" \
      de.qikvrt.source-tree="$QIKVRT_SOURCE_TREE"
COPY tools/qikvrt_self_host.py /opt/qikvrt-firefox-upgrade/qikvrt_self_host.py
RUN python3 -B /opt/qikvrt-firefox-upgrade/qikvrt_self_host.py firefox-release-provision \
      --output /opt/qikvrt/runtime/firefox-release
ENV QIKVRT_FIREFOX_BINARY=/usr/lib/firefox/firefox
USER 10001:10001

FROM ${QIKVRT_PRODUCTION_IMAGE} AS package-builder
USER root
ARG DEBIAN_SNAPSHOT=20261013T000000Z
RUN printf 'Types: deb\nURIs: https://snapshot.debian.org/archive/debian/%s\nSuites: bookworm bookworm-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n\nTypes: deb\nURIs: https://snapshot.debian.org/archive/debian-security/%s\nSuites: bookworm-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n' "$DEBIAN_SNAPSHOT" "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-upgrade --no-install-recommends git make \
    && git config --system --add safe.directory /source \
    && rm -rf /var/lib/apt/lists/* /var/log/apt/* /var/log/dpkg.log /var/log/alternatives.log
WORKDIR /source
ARG QIKVRT_SOURCE_HEAD
ARG QIKVRT_SOURCE_TREE
COPY . /source
RUN python3 -B tools/qikvrt_self_host.py pack --root /source \
      --expected-head "$QIKVRT_SOURCE_HEAD" --expected-tree "$QIKVRT_SOURCE_TREE" \
      --browser-assets-root /usr/share/novnc --firefox-package firefox --output /out/package > /out-build-receipt.json \
    && python3 -B tools/qikvrt_self_host.py verify --root /out/package \
      --manifest-sha256 "$(python3 -c 'import json; print(json.load(open("/out-build-receipt.json"))["manifest_sha256"])')"

FROM ${QIKVRT_PRODUCTION_IMAGE} AS production
ARG QIKVRT_SOURCE_HEAD
ARG QIKVRT_SOURCE_TREE
LABEL org.opencontainers.image.source="https://github.com/ingolf-lohmann/qik-vrt" \
      org.opencontainers.image.revision="$QIKVRT_SOURCE_HEAD" \
      org.opencontainers.image.version="s1-1.12.0" \
      org.opencontainers.image.licenses="PolyForm-Noncommercial-1.0.0" \
      de.qikvrt.source-tree="$QIKVRT_SOURCE_TREE"
COPY --from=package-builder --chown=10001:10001 /out/package /opt/qikvrt
COPY --from=qikvrt-signed-extension /standard.xpi /usr/lib/firefox/distribution/extensions/qikvrt-ai-terminal@goldkelch.local.xpi
ENV QIKVRT_FIREFOX_BINARY=/usr/lib/firefox/firefox
WORKDIR /opt/qikvrt
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/terminal',timeout=3)); assert r['state']=='NATIVE_TEMDD_READY'"]
ENTRYPOINT ["python3", "/opt/qikvrt/tools/qikvrt_self_host.py", "run", "--root", "/opt/qikvrt"]
# Missing private configuration/manifest pin is deliberately not an admitted run.
CMD ["--help"]
