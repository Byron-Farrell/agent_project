"""Comment on a pull request with tests added or changed on the branch.

Allure supplies each test's title, the note on what it checks and why, and
its steps. Classification uses the test source compared with the base branch.
Status transitions from the Allure report (fixed, regressed, malfunctioned)
are included as updates even when the source is unchanged.
"""

import argparse
import ast
import json
import os
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path

MARKER = "<!-- allure-pr-tests -->"
STATUS_UPDATES = {"fixed", "regressed", "malfunctioned"}


@dataclass(frozen=True)
class TestEntry:
    qualname: str
    kind: str
    title: str
    status: str
    description: str
    steps: tuple[str, ...]


def tests_in(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    lines = source.splitlines(keepends=True)
    found: dict[str, str] = {}

    def visit(node: ast.AST, class_names: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, (*class_names, child.name))
                continue
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if child.name.startswith("test_"):
                    qual = ".".join((*class_names, child.name))
                    found[qual] = _span(child, lines)
                continue
            visit(child, class_names)

    visit(tree, ())
    return found


def classify_source(base: str | None, head: str) -> tuple[list[str], list[str]]:
    base_tests = tests_in(base) if base is not None else {}
    head_tests = tests_in(head)
    new = [name for name in head_tests if name not in base_tests]
    updated = [
        name
        for name, body in head_tests.items()
        if name in base_tests and base_tests[name] != body
    ]
    return sorted(new), sorted(updated)


def _span(node: ast.AST, lines: list[str]) -> str:
    start = node.lineno
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.decorator_list
    ):
        start = min(decorator.lineno for decorator in node.decorator_list)
    end = node.end_lineno or node.lineno
    return "".join(lines[start - 1 : end])


def collect_changes(root: Path, base: str) -> list[tuple[str, str]]:
    changes: list[tuple[str, str]] = []
    for head_path, base_path in _changed_test_paths(root, base):
        head_source = (root / head_path).read_text()
        base_source = _show_file(root, base, base_path) if base_path else None
        added, edited = classify_source(base_source, head_source)
        for name in added:
            changes.append((_qualname(head_path, name), "new"))
        for name in edited:
            changes.append((_qualname(head_path, name), "updated"))
    return changes


def load_results(results_dir: Path) -> list[dict]:
    if not results_dir.is_dir():
        return []
    results = []
    for path in sorted(results_dir.glob("*-result.json")):
        results.append(json.loads(path.read_text()))
    return results


def status_changes(report_dir: Path) -> list[tuple[str, str]]:
    """Return (qualname, kind) for Allure status transitions worth listing."""
    details = report_dir / "data" / "test-results"
    if not details.is_dir():
        return []
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for path in sorted(details.glob("*.json")):
        test = json.loads(path.read_text())
        transition = str(test.get("transition") or "")
        full_name = test.get("fullName") or ""
        if transition not in STATUS_UPDATES or not full_name:
            continue
        qualname = _normalize_full_name(full_name)
        if qualname in seen:
            continue
        seen.add(qualname)
        found.append((qualname, "updated"))
    return found


def render(entries: list[TestEntry]) -> str:
    lines = [
        MARKER,
        "## New and updated tests",
        "",
        "Tests added or changed relative to the base branch, plus any test",
        "whose status changed since the Allure history on the default branch.",
        "Descriptions and steps come from this run's Allure results.",
        "",
    ]
    run_url = _run_url()
    if run_url:
        lines.append(
            f"Allure report artifact: `allure-report` on [this run]({run_url})."
        )
        lines.append("")
    if not entries:
        lines.append("No tests were added or changed.")
        return "\n".join(lines) + "\n"

    for kind, heading in (("new", "New"), ("updated", "Updated")):
        group = [entry for entry in entries if entry.kind == kind]
        if not group:
            continue
        lines.append(f"### {heading}")
        lines.append("")
        for entry in group:
            lines.extend(_render_entry(entry))
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def upsert_comment(body: str) -> None:
    number = os.environ.get("PR_NUMBER", "").strip()
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not number or not repository:
        print(body)
        return

    comments = _gh_json(f"repos/{repository}/issues/{number}/comments")
    match = next(
        (comment for comment in comments if MARKER in comment.get("body", "")), None
    )
    payload = json.dumps({"body": body})
    if match is None:
        _gh_input("POST", f"repos/{repository}/issues/{number}/comments", payload)
        return
    _gh_input("PATCH", f"repos/{repository}/issues/comments/{match['id']}", payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=os.environ.get("BASE_SHA", ""))
    parser.add_argument("--results", type=Path, default=Path("allure-results"))
    parser.add_argument("--report", type=Path, default=Path("allure-report"))
    args = parser.parse_args()
    if not args.base:
        raise SystemExit("Pass --base or set BASE_SHA to the pull request base commit.")

    root = _repo_root()
    indexed = {qualname: kind for qualname, kind in collect_changes(root, args.base)}
    for qualname, kind in status_changes(args.report):
        indexed.setdefault(qualname, kind)

    by_name = _results_by_qualname(load_results(args.results))
    entries = [
        _entry(qualname, kind, by_name.get(qualname))
        for qualname, kind in sorted(
            indexed.items(), key=lambda item: (item[1] != "new", item[0])
        )
    ]
    body = render(entries)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(body)
    upsert_comment(body)


def _entry(qualname: str, kind: str, result: dict | None) -> TestEntry:
    if result is None:
        return TestEntry(qualname, kind, qualname.rsplit(".", 1)[-1], "not run", "", ())
    description = textwrap.dedent(str(result.get("description") or "")).strip()
    return TestEntry(
        qualname=qualname,
        kind=kind,
        title=str(result.get("name") or qualname.rsplit(".", 1)[-1]),
        status=str(result.get("status") or "unknown"),
        description=description,
        steps=tuple(_step_lines(result.get("steps") or [])),
    )


def _results_by_qualname(results: list[dict]) -> dict[str, dict]:
    chosen: dict[str, dict] = {}
    for result in results:
        full_name = result.get("fullName") or ""
        if not full_name:
            continue
        qualname = _normalize_full_name(full_name)
        current = chosen.get(qualname)
        if current is None or (result.get("stop") or 0) >= (current.get("stop") or 0):
            chosen[qualname] = result
    return chosen


def _step_lines(steps: list[dict], depth: int = 0) -> list[str]:
    lines: list[str] = []
    for index, step in enumerate(steps, start=1):
        title = str(step.get("name") or "step")
        indent = "   " * depth
        marker = f"{index}." if depth == 0 else "-"
        lines.append(f"{indent}{marker} {title}")
        lines.extend(_step_lines(step.get("steps") or [], depth + 1))
    return lines


def _render_entry(entry: TestEntry) -> list[str]:
    lines = [
        f"#### {entry.title}",
        "",
        f"`{entry.qualname}` — {entry.status}",
        "",
    ]
    if entry.description:
        lines.append(entry.description)
        lines.append("")
    if entry.steps:
        lines.append("Steps:")
        lines.append("")
        lines.extend(entry.steps)
    return lines


def _changed_test_paths(root: Path, base: str) -> list[tuple[str, str | None]]:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--name-status",
            "--diff-filter=AMR",
            base,
            "HEAD",
            "--",
            "backend",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[tuple[str, str | None]] = []
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("R") and len(parts) == 3:
            old, new = parts[1], parts[2]
            if _is_test_file(new):
                paths.append((new, old if _is_test_file(old) else None))
            continue
        if status in {"A", "M"} and len(parts) == 2 and _is_test_file(parts[1]):
            paths.append((parts[1], None if status == "A" else parts[1]))
    return paths


def _is_test_file(path: str) -> bool:
    name = Path(path).name
    return name.startswith("test_") and name.endswith(".py")


def _show_file(root: Path, rev: str, path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _qualname(path: str, name: str) -> str:
    relative = path.removeprefix("backend/")
    module = relative.removesuffix(".py").replace("/", ".")
    return f"{module}.{name}"


def _normalize_full_name(full_name: str) -> str:
    return full_name.split("[", 1)[0].replace("#", ".")


def _run_url() -> str:
    repository = os.environ.get("GITHUB_REPOSITORY", "").strip()
    run_id = os.environ.get("GITHUB_RUN_ID", "").strip()
    if not repository or not run_id:
        return ""
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    return f"{server}/{repository}/actions/runs/{run_id}"


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.strip())


def _gh_json(endpoint: str) -> list[dict]:
    result = subprocess.run(
        ["gh", "api", "--paginate", endpoint],
        check=True,
        capture_output=True,
        text=True,
    )
    if not result.stdout.strip():
        return []
    payload = json.loads(result.stdout)
    if isinstance(payload, list):
        return payload
    return []


def _gh_input(method: str, endpoint: str, payload: str) -> None:
    subprocess.run(
        ["gh", "api", "--method", method, endpoint, "--input", "-"],
        input=payload,
        text=True,
        check=True,
    )


if __name__ == "__main__":
    main()
