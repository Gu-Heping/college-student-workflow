#!/usr/bin/env python3
"""Sanitize stdin for GitHub publishing, then optionally run a follow-up command.

Bare shell pipes such as ``prepare_github_issue.py --stdin | gh issue create -F -``
still invoke ``gh`` when the left-hand side exits non-zero unless ``pipefail`` is
set — which creates empty issue / review / comment bodies. This wrapper only
runs the downstream command when sanitization succeeds.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

from prepare_github_issue import sanitize_stdin_payload


def split_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    if "--" not in argv:
        return argv, []
    index = argv.index("--")
    return argv[:index], argv[index + 1 :]


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    our_argv, command = split_argv(raw_argv)

    parser = argparse.ArgumentParser(
        description=(
            "Sanitize stdin with the same privacy rules as prepare_github_issue.py, "
            "then optionally feed the sanitized body to a gh command after --."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Sanitize only (print sanitized text to stdout). Do not run a follow-up command.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Report privacy findings to stderr only; exit non-zero on blockers or warnings.",
    )
    parser.add_argument(
        "--stdin-format",
        choices=["text", "json"],
        default="text",
        help='Input format. json accepts gh-style {"body": "..."} payloads.',
    )
    parser.add_argument(
        "--allow-privacy-warnings",
        action="store_true",
        help="Emit/post the sanitized draft even when privacy warnings are present.",
    )
    args = parser.parse_args(our_argv)

    if args.check and command:
        raise SystemExit("--check cannot be combined with a follow-up command after --")
    if args.check_only and command:
        raise SystemExit("--check-only cannot be combined with a follow-up command after --")

    exit_code, output = sanitize_stdin_payload(
        sys.stdin.read(),
        stdin_format=args.stdin_format,
        allow_privacy_warnings=args.allow_privacy_warnings,
        check_only=args.check_only,
    )
    if exit_code != 0:
        return exit_code
    if args.check_only:
        return 0
    if output is None:
        return 1

    if args.check or not command:
        sys.stdout.write(output)
        return 0

    result = subprocess.run(
        command,
        input=output,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
