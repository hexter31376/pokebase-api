"""Create a draft PR for a pushed branch and refresh only marked generated sections."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlencode


def api(path, payload=None, method="POST"):
    command = ["gh", "api", path]
    if payload is not None:
        command.extend(["--method", method, "--input", "-"])
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def git(*args):
    return subprocess.run(
        ["git", *args], text=True, capture_output=True, check=True,
    ).stdout


def collect_changes(base, sha):
    base_sha = git("rev-parse", "--verify", f"refs/remotes/origin/{base}^{{commit}}").strip()
    merge_base = git("merge-base", base_sha, sha).strip()
    records = git("log", "--reverse", "--format=%H%x00%s%x00", f"{base_sha}..{sha}")
    parts = records.split("\0")
    commits = [
        {"sha": parts[i].strip(), "commit": {"message": parts[i + 1]}}
        for i in range(0, len(parts) - 1, 2)
    ]
    files = []
    stats = git("diff", "--no-ext-diff", "--no-renames", "--numstat", "-z", merge_base, sha)
    for record in stats.split("\0"):
        if record:
            added, deleted, path = record.split("\t", 2)
            files.append({"path": path, "added": added, "deleted": deleted})
    return {"commits": commits, "files": files, "merge_base": merge_base}


def safe_text(value):
    value = value.replace("@", "＠").replace("#", "＃")
    value = value.replace("<", "&lt;").replace(">", "&gt;")
    return value.replace("`", "＇").replace("\n", " ").replace("\r", " ")


def build_body(template, changes, repo, base, sha):
    headings = ["변경 요약", "주요 변경 사항", "검증", "관련 이슈"]
    if any(f"## {heading}" not in template for heading in headings):
        raise ValueError("PR template headings changed; update auto_pr.py accordingly")
    commits, files = changes["commits"], changes["files"]
    added = sum(int(f["added"]) for f in files if f["added"] != "-")
    deleted = sum(int(f["deleted"]) for f in files if f["deleted"] != "-")
    binary = sum(f["added"] == "-" for f in files)
    comparison = f"https://github.com/{repo}/compare/{changes['merge_base']}...{sha}"
    summary = (
        f"- {safe_text(base)}와의 분기점부터 작업 브랜치 전체 변경을 집계했습니다.\n"
        f"- 커밋 {len(commits)}개, 변경 파일 {len(files)}개, 텍스트 +{added}/-{deleted}줄, 바이너리 {binary}개\n"
        f"- [전체 변경 확인]({comparison})\n"
        "- 구현 의도와 변경 후 동작은 리뷰 전에 보완해주세요."
    )
    lines = ["### 변경 파일", ""]
    for item in files[:100]:
        lines.append(f"- `{safe_text(item['path'])[:200]}` (+{item['added']}/-{item['deleted']})")
    if len(files) > 100:
        lines.append(f"- 나머지 {len(files) - 100}개 파일은 전체 변경 링크 참조")
    lines.extend(["", "### 브랜치 커밋", ""])
    for commit in commits[:50]:
        lines.append(f"- {commit['sha'][:7]}: {safe_text(commit['commit']['message'])[:200]}")
    if len(commits) > 50:
        lines.append(f"- 나머지 {len(commits) - 50}개 커밋은 전체 변경 링크 참조")
    sections = {
        "변경 요약": summary,
        "주요 변경 사항": "\n".join(lines),
        "검증": "- 검증 명령: 미실행\n- 결과: PR 생성 워크플로는 빌드·테스트를 실행하지 않습니다. CI 결과를 확인해주세요.",
        "관련 이슈": "- 확인 후 `Refs #번호` 또는 해결이 완료된 경우 `Closes #번호`를 작성해주세요.",
    }
    body = re.sub(r"<!--.*?-->", "", template, flags=re.S).strip()
    for heading, content in sections.items():
        pattern = rf"(^## {re.escape(heading)}\s*\n).*?(?=^## |\Z)"
        body = re.sub(pattern, lambda m: m[1] + "\n" + content + "\n\n", body, flags=re.M | re.S)
    for heading in ("변경 요약", "주요 변경 사항"):
        content = sections[heading]
        body = body.replace(content, f"<!-- auto-pr:{heading}:start -->\n{content}\n<!-- auto-pr:{heading}:end -->", 1)
    return body.strip()


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    branch = os.environ["GITHUB_REF_NAME"]
    base = os.environ.get("PR_BASE", "develop")
    if not branch.startswith(("feature/", "fix/")) or branch == base:
        print("Not a PR source branch; skipped.")
        return
    prefix = f"repos/{repo}"
    query = urlencode({"state": "open", "head": f"{repo.split('/')[0]}:{branch}"})
    existing = api(f"{prefix}/pulls?{query}")
    if existing and existing[0]["base"]["ref"] != base:
        print("Existing PR targets a different base; preserved.")
        return
    if existing and "<!-- auto-pr:변경 요약:start -->" not in (existing[0].get("body") or ""):
        print("Existing PR has no generated sections; preserved.")
        return
    # Re-runs summarize the current remote branch instead of restoring an old snapshot.
    sha = git("rev-parse", "--verify", f"refs/remotes/origin/{branch}^{{commit}}").strip()
    changes = collect_changes(base, sha)
    if not changes["commits"] or not changes["files"]:
        print("No commits ahead of base; skipped.")
        return
    commits = changes["commits"]
    title = (commits[0]["commit"]["message"] if len(commits) == 1
             else f"{branch}: 브랜치 변경 통합")[:200]
    template = Path(".github/pull_request_template.md").read_text()
    body = build_body(template, changes, repo, base, sha)
    if existing:
        current = api(f"{prefix}/pulls/{existing[0]['number']}")
        updated = current.get("body") or ""
        for heading in ("변경 요약", "주요 변경 사항"):
            pattern = rf"<!-- auto-pr:{heading}:start -->.*?<!-- auto-pr:{heading}:end -->"
            generated = re.search(pattern, body, flags=re.S).group(0)
            updated = re.sub(pattern, lambda _: generated, updated, flags=re.S)
        if updated != (current.get("body") or ""):
            api(f"{prefix}/pulls/{current['number']}", {"body": updated}, method="PATCH")
        print(f"Generated sections refreshed: {current['html_url']}")
        return
    try:
        pr = api(f"{prefix}/pulls", {
            "title": title, "body": body, "base": base, "head": branch, "draft": True,
        })
    except subprocess.CalledProcessError as error:
        # A manual creation can race with this job. Suppress only a confirmed duplicate.
        existing = api(f"{prefix}/pulls?{query}")
        if not existing:
            print(error.stderr, file=sys.stderr)
            raise
        pr = existing[0]
    print(f"Draft PR available: {pr['html_url']}")


if __name__ == "__main__":
    main()
