# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# New S1 provisioning/test adapter; historical deployment originals stay intact.
# No provider checkout, gh, credentials or account setup in the runtime image.
ARG SOURCE_DATE_EPOCH
ARG RUNTIME_CARRIER=runtime-built
FROM node:24-bookworm-slim@sha256:0e0ff40c39bc087845bfb27465a0df4ea419520094bc35842ff83dd8cbe6f9b6 AS node-runtime
FROM python:3.12-slim-bookworm@sha256:54c85f3c47607a77f32adec749d3c81d1348bf25833671f512b26a9b6d778cb3 AS runtime-built
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
ARG DEBIAN_SNAPSHOT=20261013T000000Z
RUN printf 'Types: deb\nURIs: https://snapshot.debian.org/archive/debian/%s\nSuites: bookworm bookworm-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n\nTypes: deb\nURIs: https://snapshot.debian.org/archive/debian-security/%s\nSuites: bookworm-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n' "$DEBIAN_SNAPSHOT" "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
      firefox-esr libstdc++6 novnc websockify x11-utils x11vnc xvfb ca-certificates \
    && dpkg-query -W -f='${Package}\t${Version}\n' > /usr/local/share/qikvrt-distribution-packages.tsv \
    && rm -rf /var/lib/apt/lists/* /var/log/apt/* /var/log/dpkg.log /var/log/alternatives.log
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1
# This is a provisioned dependency image. Operators transfer a separately
# frozen package and private config/volume; no mutable checkout at runtime.
WORKDIR /source
FROM ${RUNTIME_CARRIER} AS runtime
# CI supplies the original PR494 OCI image as a digest-bound named context.
# The default provisioned test carrier remains available to original tests.
FROM runtime AS test
ARG DEBIAN_SNAPSHOT=20261013T000000Z
RUN printf 'Types: deb\nURIs: https://snapshot.debian.org/archive/debian/%s\nSuites: bookworm bookworm-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n\nTypes: deb\nURIs: https://snapshot.debian.org/archive/debian-security/%s\nSuites: bookworm-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n' "$DEBIAN_SNAPSHOT" "$DEBIAN_SNAPSHOT" > /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-upgrade --no-install-recommends git make \
    && git config --system --add safe.directory /source \
    && rm -rf /var/lib/apt/lists/* /var/log/apt/* /var/log/dpkg.log /var/log/alternatives.log

# Reuse the exact S1 exporter and original native terminal. The build context
# is produced by container-context, with no Git credentials or runtime state.
FROM test AS package-builder
ARG QIKVRT_SOURCE_HEAD
ARG QIKVRT_SOURCE_TREE
COPY . /source
RUN python3 -B tools/qikvrt_self_host.py pack --root /source \
      --expected-head "$QIKVRT_SOURCE_HEAD" --expected-tree "$QIKVRT_SOURCE_TREE" \
      --browser-assets-root /usr/share/novnc --output /out/package > /out-build-receipt.json \
    && python3 -B tools/qikvrt_self_host.py verify --root /out/package \
      --manifest-sha256 "$(python3 -c 'import json; print(json.load(open("/out-build-receipt.json"))["manifest_sha256"])')"

FROM runtime AS production
ARG QIKVRT_SOURCE_HEAD
ARG QIKVRT_SOURCE_TREE
LABEL org.opencontainers.image.source="https://github.com/ingolf-lohmann/qik-vrt" \
      org.opencontainers.image.revision="$QIKVRT_SOURCE_HEAD" \
      org.opencontainers.image.version="s1-1.6.1" \
      org.opencontainers.image.licenses="PolyForm-Noncommercial-1.0.0" \
      de.qikvrt.source-tree="$QIKVRT_SOURCE_TREE"
COPY --from=package-builder --chown=10001:10001 /out/package /opt/qikvrt
WORKDIR /opt/qikvrt
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python3", "-c", "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/terminal',timeout=3)); assert r['state']=='NATIVE_TEMDD_READY'"]
ENTRYPOINT ["python3", "/opt/qikvrt/tools/qikvrt_self_host.py", "run", "--root", "/opt/qikvrt"]
# Missing private configuration/manifest pin is deliberately not an admitted run.
CMD ["--help"]
