"""Small source-tree scanner. Reports paths and line numbers, never matched values."""

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"/" + r"Users/[^/\s]+/"),
]


def main():
    # An independent project root is required; do not scan a containing repo.
    if (ROOT / ".git").exists():
        result = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"], capture_output=True, check=True)
        paths = [ROOT / name for name in result.stdout.decode().split("\0") if name]
    else:
        excluded = {".git", ".venv", "venv", "__pycache__", "build", "dist"}
        paths = [path for path in ROOT.rglob("*") if path.is_file() and not (set(path.relative_to(ROOT).parts) & excluded)
                 and not any(part.endswith(".egg-info") for part in path.parts)]
    findings = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeError:
            continue
        for index, line in enumerate(lines, 1):
            if any(pattern.search(line) for pattern in PATTERNS):
                findings.append(f"{path.relative_to(ROOT)}:{index}: potential secret or personal path")
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print(f"Source scan passed ({len(paths)} files); this is not a complete secret audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
