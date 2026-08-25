"""Container runtime entrypoint and health-check CLI (INF_CMP_001).

Wires the ARC_CMP_009 health aggregator into a process the compute
environment (the root `Dockerfile`) can invoke for its HEALTHCHECK and as
its default command -- the reproducible run/restart/health-check cycle
required by INF_REQ_001.

No dependency check is registered yet: at m02 the platform has no live
external dependency to probe (in-memory stores only, no wired channel or
model/tool gateway process). A later milestone registers real checks here
as those pieces come online; until then this reports trivially healthy.
"""

from __future__ import annotations

import json
import os
import sys

from .health import HealthAggregator


def build_health_aggregator() -> HealthAggregator:
    """Build the aggregator this environment's HEALTHCHECK reports on."""
    return HealthAggregator()


def main() -> int:
    """Print a JSON health report and return the process exit code.

    `APP_VERSION` is baked into the image at build time (see `Dockerfile`)
    so the report identifies which build is running (INF_REQ_010).
    """
    report = build_health_aggregator().report()
    payload = {
        "healthy": report.healthy,
        "version": os.environ.get("APP_VERSION", "unknown"),
        "dependencies": [
            {"name": dependency.name, "healthy": dependency.healthy, "detail": dependency.detail}
            for dependency in report.dependencies
        ],
    }
    print(json.dumps(payload))
    return 0 if report.healthy else 1


if __name__ == "__main__":
    sys.exit(main())
