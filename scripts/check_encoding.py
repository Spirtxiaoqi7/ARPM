"""
ARPM 源码编码巡检脚本

默认扫描 code/arpm-app 目录下常见源码与文档文件，检查是否能被 UTF-8 正常解码。
可选输出 JSON 报告，便于后续自动化或留档。
"""
import argparse
import json
from pathlib import Path


TEXT_EXTENSIONS = {
    ".py", ".md", ".txt", ".bat", ".js", ".css", ".html",
    ".yaml", ".yml", ".json"
}


def detect_utf8_issues(root: Path) -> list[dict]:
    issues = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            issues.append({
                "file": str(path),
                "reason": "not_valid_utf8",
                "position": exc.start,
                "details": str(exc),
            })

    return issues


def build_report(root: Path) -> dict:
    issues = detect_utf8_issues(root)
    return {
        "root": str(root),
        "status": "ok" if not issues else "has_issues",
        "checked_extensions": sorted(TEXT_EXTENSIONS),
        "issue_count": len(issues),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 ARPM 源码文件是否为合法 UTF-8。")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="要扫描的目录，默认是 code/arpm-app",
    )
    parser.add_argument(
        "--json-out",
        help="可选：将检查结果写入 JSON 文件",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root)

    print("=" * 60)
    print("ARPM 编码巡检")
    print("=" * 60)
    print(f"[扫描目录] {root}")
    print(f"[检查结果] {report['status']}")
    print(f"[问题数量] {report['issue_count']}")

    if report["issues"]:
        print()
        print("[异常文件]")
        for item in report["issues"]:
            print(f"- {item['file']}")
            print(f"  reason: {item['reason']}")
            print(f"  position: {item['position']}")
            print(f"  details: {item['details']}")
    else:
        print("[OK] 所有目标文件均可按 UTF-8 正常解码")

    if args.json_out:
        output = Path(args.json_out).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[报告已写入] {output}")

    return 0 if not report["issues"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
