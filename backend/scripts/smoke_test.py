"""End-to-end smoke and security verification script for local or Render deployments."""

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from scripts.smoke_checks_endpoints import (  # noqa: E402
    SmokeRunner,
    cleanup_smoke_data,
    login_user,
    run_endpoint_checks,
)
from scripts.smoke_checks_security import run_security_checks  # noqa: E402


def main() -> int:
    """Run endpoint and security smoke checks and exit non-zero on any failure."""
    parser = argparse.ArgumentParser(description="Run API smoke and security checks.")
    parser.add_argument(
        "--safe",
        action="store_true",
        help="Read-only mode: skip checks that write data or trigger rate limits.",
    )
    args = parser.parse_args()

    base_url = os.getenv("BASE_URL", "").strip()
    admin_email = (os.getenv("SMOKE_ADMIN_EMAIL") or os.getenv("ADMIN_EMAIL") or "").strip()
    admin_pw = (os.getenv("SMOKE_ADMIN_PASSWORD") or os.getenv("ADMIN_PASSWORD") or "").strip()
    vol_email = (os.getenv("SMOKE_VOLUNTEER_EMAIL") or os.getenv("VOLUNTEER_EMAIL") or "").strip()
    vol_pw = (os.getenv("SMOKE_VOLUNTEER_PASSWORD") or os.getenv("VOLUNTEER_PASSWORD") or "").strip()

    missing = [
        k
        for k, v in (
            ("BASE_URL", base_url),
            ("SMOKE_ADMIN_EMAIL/ADMIN_EMAIL", admin_email),
            ("SMOKE_ADMIN_PASSWORD/ADMIN_PASSWORD", admin_pw),
            ("SMOKE_VOLUNTEER_EMAIL/VOLUNTEER_EMAIL", vol_email),
            ("SMOKE_VOLUNTEER_PASSWORD/VOLUNTEER_PASSWORD", vol_pw),
        )
        if not v
    ]
    if missing:
        print(f"ERROR: Missing required env vars: {', '.join(missing)}", file=sys.stderr)
        return 1

    runner = SmokeRunner(base_url=base_url)
    admin_token = login_user(runner, admin_email, admin_pw, "admin")
    vol_token = login_user(runner, vol_email, vol_pw, "volunteer")
    if not admin_token or not vol_token:
        print(f"\nSummary: {runner.passed} passed, {runner.failed} failed, {runner.skipped} skipped")
        return 1

    ctx: dict = {}
    try:
        ctx = run_endpoint_checks(runner, admin_token, vol_token, safe_mode=args.safe)
        run_security_checks(runner, admin_token, vol_token, ctx, safe_mode=args.safe)
    finally:
        if not args.safe:
            cleanup_smoke_data(runner, admin_token, ctx)

    print(f"\nSummary: {runner.passed} passed, {runner.failed} failed, {runner.skipped} skipped")
    return 1 if runner.failed else 0


if __name__ == "__main__":
    sys.exit(main())
