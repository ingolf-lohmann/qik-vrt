FROM python:3.13-alpine
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080 QIKVRT_QA_ENABLED=false
WORKDIR /app
RUN addgroup -S qikvrt && adduser -S -G qikvrt -u 10001 qikvrt
COPY runtime/public_qa/ /app/runtime/public_qa/
COPY docs/fragen/index.html /app/docs/fragen/index.html
COPY docs/assets/js/qikvrt-questions.js docs/assets/js/qikvrt-local-engine.js /app/docs/assets/js/
COPY docs/assets/css/qikvrt.css /app/docs/assets/css/qikvrt.css
COPY docs/CURRENT_AUTHORITY.md docs/BOUNDARIES.md docs/ARCHITECTURE.md /app/docs/
COPY docs/publications/index.json /app/docs/publications/index.json
USER qikvrt
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=4s --start-period=5s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8080/api/health',timeout=3).close()"
CMD ["python", "-m", "runtime.public_qa.server"]
