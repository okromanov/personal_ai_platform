# Reproducible compute runtime environment (INF_CMP_001).
#
# Implements INF_REQ_001 (supported OS, reproducible install/run/restart/
# health-check), INF_REQ_002 (application runs without administrative
# privileges) and INF_REQ_010 (identifiable deployed version). This image
# has no third-party runtime dependency yet -- the platform's own code is
# stdlib-only at m02 -- so no dependency install step exists until one is
# needed.
#
# INF_REQ_015: dev and prod carry different evidence. A green local
# `operations/scripts/quality/run_suite.py` run (developer's own Python
# environment, no admin privileges, no production data) does not certify
# this build -- only a built, versioned image run from this Dockerfile is
# this runtime environment's own evidence.
FROM python:3.12-slim

ARG APP_VERSION=unknown
ENV APP_VERSION=${APP_VERSION} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

LABEL org.opencontainers.image.version=${APP_VERSION}

# INF_REQ_002: the application user has no administrative privileges.
# Administrative access to the host or image build is a separate,
# out-of-band concern this image does not grant.
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app

WORKDIR /app
COPY src ./src
RUN chown -R app:app /app
USER app

# INF_REQ_001: the reproducible health-check half of the install/run/
# restart/health-check cycle. No dependency check is registered yet (see
# src/operations/health_check.py) -- a wired channel/model gateway process
# registers real checks in a later milestone.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "-m", "src.operations.health_check"]

CMD ["python", "-m", "src.operations.health_check"]
