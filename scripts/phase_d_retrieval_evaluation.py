"""Entry point reserved for the gated Phase D retrieval evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path

from sciscope.evaluation.runner import (
    EvaluationAuthorizationError,
    require_evaluation_authorizations,
    require_preflight_authorization,
)


def main() -> int:
    """Validate authorization artifacts without accessing protected data."""
    parser = argparse.ArgumentParser(description=__doc__)
    checks = parser.add_mutually_exclusive_group(required=True)
    checks.add_argument("--check-preflight-authorization", action="store_true")
    checks.add_argument(
        "--check-retrieval-authorizations",
        "--check-authorizations",
        dest="check_retrieval_authorizations",
        action="store_true",
        help=(
            "Validate both distinct T005 and T006 records "
            "(legacy alias supported)."
        ),
    )
    parser.add_argument("--preflight-authorization", type=Path)
    parser.add_argument("--retrieval-authorization", type=Path)
    parser.add_argument("--cohort")
    args = parser.parse_args()
    if args.check_preflight_authorization:
        if not args.preflight_authorization or not args.cohort:
            parser.error(
                "preflight checks require --preflight-authorization "
                "and --cohort"
            )
        if args.retrieval_authorization:
            parser.error(
                "preflight-only checks do not accept retrieval authorization"
            )
        try:
            require_preflight_authorization(
                args.preflight_authorization, expected_cohort=args.cohort
            )
        except EvaluationAuthorizationError as error:
            parser.error(str(error))
        print("Preflight authorization is valid; no data was accessed.")
        return 0

    if not args.preflight_authorization or not args.retrieval_authorization:
        parser.error(
            "retrieval checks require both distinct authorization paths"
        )
    if args.cohort:
        parser.error("--cohort is only valid for preflight-only checks")
    try:
        require_evaluation_authorizations(
            args.preflight_authorization, args.retrieval_authorization
        )
    except EvaluationAuthorizationError as error:
        parser.error(str(error))
    print(
        "Both authorization records structurally match; no data was accessed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
