"""CLI entry point; the default command runs the MCP stdio server."""

import argparse
import asyncio
import getpass
import json
import subprocess
import sys
from pathlib import Path

from .client import DeepSeekError, list_models, validate_key


def setup_key() -> None:
    if sys.platform != "darwin":
        raise DeepSeekError("setup-key requires macOS. On other platforms set DEEPSEEK_API_KEY in the server environment.")
    key = validate_key(getpass.getpass("DeepSeek API Key (hidden): "))
    helper = Path(__file__).with_name("keychain_credential.swift")
    try:
        result = subprocess.run(
            ["/usr/bin/swift", str(helper), "set"], input=key,
            text=True, capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DeepSeekError("Could not run the Keychain helper. Check Swift / Xcode Command Line Tools.") from exc
    if result.returncode:
        raise DeepSeekError("Could not save key to macOS Keychain. Check the Keychain access prompt and Swift installation.")
    print("DeepSeek key saved to macOS Keychain.")


def main() -> int:
    parser = argparse.ArgumentParser(description="DeepSeek second opinions inside Codex via MCP.")
    parser.add_argument("command", nargs="?", choices=("serve", "models", "setup-key"), default="serve")
    args = parser.parse_args()
    try:
        if args.command == "serve":
            from .server import run
            run()
        elif args.command == "models":
            print(json.dumps(asyncio.run(list_models()), ensure_ascii=False, indent=2))
        else:
            setup_key()
    except DeepSeekError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
