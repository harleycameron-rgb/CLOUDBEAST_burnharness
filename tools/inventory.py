"""Inventory sibling Git repositories without changing them or using the network."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import re
import subprocess


EXCLUDED = {".git", "node_modules", "dist", "build", "__pycache__", ".venv"}
TEST_PATTERNS = ("test_*.py", "*_test.py", "*.test.js", "*.test.ts", "*.spec.*")
PYTEST_SECTION = re.compile(
    r"""^\s*\[\s*(?:tool|"tool"|'tool')\s*\.\s*"""
    r"""(?:pytest|"pytest"|'pytest')\s*\.\s*"""
    r"""(?:ini_options|"ini_options"|'ini_options')\s*\]\s*(?:#.*)?$"""
)


def git_read(repo, *args):
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=30, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def read_text(path):
    if path.is_symlink():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def has_pytest_section(text):
    # Ignore section-like text inside TOML strings and comments, without
    # requiring tomllib (which is not available on Python 3.10).
    tokens = re.compile(
        r'""".*?"""|\'\'\'.*?\'\'\'|"(?:\\.|[^"\\])*"|'
        r"'[^']*'|#[^\n]*", re.DOTALL,
    )
    text = tokens.sub(
        lambda match: (
            re.sub(r"[^\n]", " ", match.group())
            if match.group().startswith(('"""', "'''", "#"))
            else match.group()
        ),
        text,
    )
    return any(PYTEST_SECTION.fullmatch(line) for line in text.splitlines())


def readme_first_line(text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        line = line.strip()
        following = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if (not line or re.match(r"^#{1,6}(?:\s|$)", line)
                or re.fullmatch(r"(?:=+|-+)", line)
                or re.fullmatch(r"(?:=+|-+)", following)):
            continue
        return line
    return "none"


def inventory_repo(repo):
    languages = Counter()
    tests = 0
    for directory, dirs, files in os.walk(repo, followlinks=False):
        dirs[:] = sorted(
            name for name in dirs
            if name not in EXCLUDED
            and not (Path(directory) / name).is_symlink()
        )
        for name in files:
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                continue
            languages[path.suffix.lower() or "(no extension)"] += 1
            tests += any(fnmatchcase(name, pattern) for pattern in TEST_PATTERNS)

    pyproject = repo / "pyproject.toml"
    package = repo / "package.json"
    commands = []
    if has_pytest_section(read_text(pyproject)):
        commands.append("pytest")
    try:
        metadata = json.loads(read_text(package))
    except (ValueError, RecursionError):
        metadata = {}
    scripts = metadata.get("scripts") if isinstance(metadata, dict) else None
    if isinstance(scripts, dict) and isinstance(scripts.get("test"), str):
        commands.append("npm test")

    readme = readme_first_line(read_text(repo / "README.md"))
    return {
        "name": repo.name,
        "remote": git_read(repo, "remote", "get-url", "origin") or "none",
        "last_commit": git_read(repo, "log", "-1", "--format=%cI") or "none",
        "commits": git_read(repo, "rev-list", "--count", "HEAD") or "0",
        "languages": languages,
        "python": pyproject.is_file() or (repo / "setup.py").is_file(),
        "node": package.is_file(),
        "tests": tests,
        "command": ", ".join(commands) or "none",
        "readme": readme,
    }


def markdown(value):
    return (str(value).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\\", "\\\\")
            .replace("|", "\\|").replace("*", "\\*")
            .replace("_", "\\_").replace("`", "\\`")
            .replace("[", "\\[").replace("]", "\\]")
            .replace("\r", " ").replace("\n", " "))


def render(workspace, repos):
    lines = [
        "# Workspace Inventory", "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Workspace: {markdown(workspace)}",
        f"Repos found: {len(repos)}", "",
        "## Summary", "",
        "| Repo | Language | Tests | Last commit | Remote |",
        "|---|---|---|---|---|",
    ]
    for repo in repos:
        language = ", ".join(
            extension for extension, count in sorted(
                repo["languages"].items(), key=lambda item: (-item[1], item[0])
            )
        ) or "none"
        cells = (repo["name"], language, repo["tests"],
                 repo["last_commit"], repo["remote"])
        lines.append("| " + " | ".join(map(markdown, cells)) + " |")
    lines.extend(["", "## Details", ""])
    for repo in repos:
        languages = ", ".join(
            f"{count} {extension}" for extension, count in sorted(
                repo["languages"].items(), key=lambda item: (-item[1], item[0])
            )
        ) or "none"
        lines.extend([
            f"### {markdown(repo['name'])}", "",
            f"- **Remote:** {markdown(repo['remote'])}",
            f"- **Last commit:** {markdown(repo['last_commit'])}",
            f"- **Commits:** {repo['commits']}",
            f"- **Languages:** {markdown(languages)}",
            f"- **Python package:** {'yes' if repo['python'] else 'no'}",
            f"- **Node package:** {'yes' if repo['node'] else 'no'}",
            f"- **Test files:** {repo['tests']}",
            f"- **Test command:** {repo['command']}",
            f"- **README:** {markdown(repo['readme'])}", "",
        ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path,
                        help="Directory containing sibling Git repositories")
    args = parser.parse_args()
    workspace = args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        parser.error(f"workspace is not a directory: {workspace}")
    try:
        repos = [
            inventory_repo(path)
            for path in sorted(workspace.iterdir(), key=lambda path: path.name)
            if not path.is_symlink() and path.is_dir()
            and not (path / ".git").is_symlink() and (path / ".git").is_dir()
        ]
        output = workspace / "REPOS.md"
        content = render(workspace, repos)
        # Do not let an existing report symlink or hard link overwrite other files.
        flags = os.O_WRONLY | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        if output.is_symlink():
            parser.error(f"refusing to overwrite a symlink: {output}")
        with os.fdopen(os.open(output, flags, 0o666), "w", encoding="utf-8") as report:
            if os.fstat(report.fileno()).st_nlink != 1:
                parser.error(f"refusing to overwrite a hard link: {output}")
            report.truncate(0)
            report.write(content)
    except OSError as error:
        parser.error(str(error))
    print(f"Wrote {output} ({len(repos)} repos)")


if __name__ == "__main__":
    main()
