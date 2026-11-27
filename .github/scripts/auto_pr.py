"""Create a draft PR for a pushed branch without modifying existing PRs."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import quote, urlencode


def api(path, payload=None):
    command = ["gh", "api", path]
    if payload is not None:
        command.extend(["--method", "POST", "--input", "-"])
    result = subprocess.run(
        command,
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def build_body(template, commits, total):
    headings = ["변경 요약", "주요 변경 사항", "검증", "관련 이슈"]
    if any(f"## {heading}" not in template for heading in headings):
        raise ValueError("PR template headings changed; update auto_pr.py accordingly")
    # Commit text is descriptive data, never a shell command or an auto-close directive.
    lines = []
    for commit in commits:
        subject = commit["commit"]["message"].splitlines()[0]
        subject = subject.replace("@", "＠").replace("#", "＃")
        subject = subject.replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f"- {commit['sha'][:7]}: {subject[:300]}")
    if total > len(commits):
        lines.append(f"- 총 {total}개 중 처음 {len(commits)}개 커밋 표시")
    sections = {
        "변경 요약": "- 커밋 목록을 기반으로 생성한 초안입니다. 실제 변경 동작을 작성해주세요.",
        "주요 변경 사항": "\n".join(lines),
        "검증": "- 검증 명령: 미실행\n- 결과: PR 생성 워크플로는 빌드·테스트를 실행하지 않습니다. CI 결과를 확인해주세요.",
        "관련 이슈": "- 확인 후 `Refs #번호` 또는 해결이 완료된 경우 `Closes #번호`를 작성해주세요.",
    }
    # Preserve the template's section order, replacing only each section body.
    body = re.sub(r"<!--.*?-->", "", template, flags=re.S).strip()
    for heading, content in sections.items():
        pattern = rf"(^## {re.escape(heading)}\s*\n).*?(?=^## |\Z)"
        body = re.sub(pattern, lambda m: m[1] + "\n" + content + "\n\n", body, flags=re.M | re.S)
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
    if existing:
        print(f"Existing PR preserved: {existing[0]['html_url']}")
        return
    # Compare to the exact pushed commit; do not accidentally describe a later push.
    sha = os.environ["GITHUB_SHA"]
    comparison = api(f"{prefix}/compare/{quote(base, safe='')}...{sha}?per_page=100")
    if comparison["ahead_by"] == 0:
        print("No commits ahead of base; skipped.")
        return
    head = api(f"{prefix}/commits/{sha}")
    title = head["commit"]["message"].splitlines()[0][:200]
    template = Path(".github/pull_request_template.md").read_text()
    body = build_body(template, comparison["commits"], comparison["total_commits"])
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
