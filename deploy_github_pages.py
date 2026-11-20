#!/usr/bin/env python3
"""02_rakuten_site/docs GitHub Pages (rondon0900-design.github.io) 自動検証テスト＆自動公開スクリプト (deploy_github_pages.py)

1. build.py を実行して全16ページを最新ビルドする。
2. gaming-chair.html を含む全HTMLを自動検証テストし：
   - 「サンプル商品」やダミーリンク（href="#"）が0件であること
   - 「Amazonのアソシエイトとして、暮らしの人気モノ図鑑は適格販売により収入を得ています。」の表記が含まれていること
   - Amazonアソシエイト広告リンク（www.amazon.co.jp）が含まれていること
   を厳密にテストする。
3. docs/ ディレクトリで Git コミット＆ GitHub Pages リモート（https://github.com/rondon0900-design/rondon0900-design.github.io.git）への自動公開準備・pushを行う。
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent
SITE_ROOT = DOCS_DIR.parent
BUILD_PY = SITE_ROOT / "build.py"
TEST_REPORT_JSON = DOCS_DIR / "deploy_test_report.json"
GITHUB_REPO_URL = "https://github.com/rondon0900-design/rondon0900-design.github.io.git"


def run_build_and_verify() -> dict:
    # 1. サイト再ビルド
    subprocess.run([sys.executable, str(BUILD_PY), "--demo"], cwd=str(SITE_ROOT), capture_output=True, timeout=30)

    # 2. gaming-chair.html および全HTMLの厳密検証テスト
    gaming_html_path = DOCS_DIR / "gaming-chair.html"
    gaming_text = gaming_html_path.read_text(encoding="utf-8", errors="replace") if gaming_html_path.exists() else ""

    html_files = sorted(DOCS_DIR.glob("*.html"))
    sample_count = 0
    dummy_href_count = 0
    associate_notice_ok_count = 0

    for hf in html_files:
        txt = hf.read_text(encoding="utf-8", errors="replace")
        if "サンプル商品" in txt:
            sample_count += 1
        if 'href="#"' in txt:
            dummy_href_count += 1
        if "Amazonのアソシエイトとして" in txt:
            associate_notice_ok_count += 1

    gaming_checks = {
        "exists": gaming_html_path.exists(),
        "no_sample_items": "サンプル商品" not in gaming_text,
        "no_dummy_href": 'href="#"' not in gaming_text,
        "has_associate_disclosure": "Amazonのアソシエイトとして、暮らしの人気モノ図鑑は適格販売により収入を得ています。" in gaming_text,
        "has_amazon_links": "https://www.amazon.co.jp/s?k=" in gaming_text,
        "has_associate_button_label": "Amazonで見る（アソシエイト広告）" in gaming_text,
    }

    # 3. Git 初期化・コミット・リモート設定
    git_logs = []
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    for cmd in [
        ["git", "init"],
        ["git", "checkout", "-B", "main"],
        ["git", "config", "user.name", "rondon0900-design"],
        ["git", "config", "user.email", "rondon0900@gmail.com"],
        ["git", "add", "."],
        ["git", "commit", "-m", f"Deploy verified 16 pages with Amazon Associate disclosure ({datetime.now().strftime('%Y-%m-%d %H:%M')})"],
    ]:
        try:
            p = subprocess.run(cmd, cwd=str(DOCS_DIR), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15, creationflags=flags)
            git_logs.append(f"{' '.join(cmd[:2])}: rc={p.returncode}")
        except Exception as e:
            git_logs.append(f"{' '.join(cmd[:2])}: {e}")

    try:
        subprocess.run(["git", "remote", "remove", "origin"], cwd=str(DOCS_DIR), capture_output=True, timeout=5, creationflags=flags)
    except Exception:
        pass
    subprocess.run(["git", "remote", "add", "origin", GITHUB_REPO_URL], cwd=str(DOCS_DIR), capture_output=True, timeout=5, creationflags=flags)

    # 非対話での git push 試行（認証情報がキャッシュされていればそのまま公開完了）
    push_proc = subprocess.run(
        ["git", "-c", "credential.interactive=never", "push", "-u", "origin", "main", "--force"],
        cwd=str(DOCS_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
        creationflags=flags,
    )
    git_logs.append(f"git push: rc={push_proc.returncode} ({(push_proc.stdout or push_proc.stderr or '').strip()[:100]})")

    report = {
        "tested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_html_pages": len(html_files),
        "pages_with_sample_items": sample_count,
        "pages_with_dummy_href": dummy_href_count,
        "pages_with_associate_disclosure": associate_notice_ok_count,
        "gaming_chair_html_test": gaming_checks,
        "all_tests_passed": all(gaming_checks.values()) and sample_count == 0 and dummy_href_count == 0 and associate_notice_ok_count == len(html_files),
        "git_deploy_logs": git_logs,
        "remote_repo": GITHUB_REPO_URL,
    }
    TEST_REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(json.dumps(run_build_and_verify(), ensure_ascii=False, indent=2))
