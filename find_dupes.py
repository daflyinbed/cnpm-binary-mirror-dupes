#!/usr/bin/env python3
"""读 npmmirror_files.jsonl，找 size + url 最后两段相同、但 /binary/ 后面包名不同的疑似重复文件。

用法:
    python3 find_dupes.py
    python3 find_dupes.py other.jsonl
"""

import json
import sys
from collections import defaultdict

INPUT = sys.argv[1] if len(sys.argv) > 1 else "npmmirror_files.jsonl"


def parse_url(url):
    """返回 (package, last_two_segments)。
    package = /binary/ 后面第一段，如 xprofiler、@journeyapps/sqlcoder
    last_two = url 路径最后两段
    """
    path = url.split("://", 1)[-1].split("?", 1)[0].split("#", 1)[0]
    parts = [p for p in path.rstrip("/").split("/") if p]
    # /-/binary/<package>/...  找 binary 的下标
    try:
        bi = parts.index("binary")
    except ValueError:
        return None, None
    after = parts[bi + 1:]
    if not after:
        return None, None
    # package 可能是 @scope/name  两段
    pkg = after[0]
    if pkg.startswith("@") and len(after) >= 2:
        pkg = after[0] + "/" + after[1]
        rel = after[2:]
    else:
        rel = after[1:]

    # 跳过 node/node-nightly/node-rc，这些版本路径段会误报
    if pkg in ("node", "node-nightly", "node-rc"):
        return None, None

    last_two = "/".join(rel[-2:]) if len(rel) >= 2 else (rel[-1] if rel else "")
    return pkg, last_two


def main():
    groups = defaultdict(list)  # (size, last_two) -> [(pkg, url), ...]
    n = 0

    with open(INPUT) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            size = obj.get("size")
            if size is None:
                continue
            pkg, last_two = parse_url(obj["url"])
            if not last_two:
                continue
            if "xprofiler" in last_two:
                file_type = "xprofiler"
            elif "keytar" in last_two:
                file_type = "keytar"
            elif "couchbase" in last_two:
                file_type = "couchbase"
            elif "libvips" in last_two:
                file_type = "libvips"
            elif "swc" in last_two:
                file_type = "swc"
            elif "better-sqlite3" in last_two:
                file_type = "better-sqlite3"   
            elif "sass_embedded" in last_two:
                file_type = "sass-embedded"
            elif "saucectl" in last_two:
                file_type = "saucectl"
            elif "robotjs" in last_two:
                file_type = "robotjs"
            elif "atom" in last_two:
                file_type = "atom"
            elif "Atom" in last_two:
                file_type = "atom"
            elif "Git" in last_two:
                file_type = "git-for-windows"
            elif "git" in last_two:
                file_type = "git-for-windows"                
            elif "utf-8-validate" in last_two:
                file_type = "utf-8-validate"
            elif "sharp" in last_two:
                file_type = "sharp"
            elif "geckodriver" in last_two:
                file_type = "geckodriver"
            else:
                file_type = "其他"
            groups[(size, last_two, file_type)].append((pkg, obj["url"]))
            n += 1
            if n % 1_000_000 == 0:
                sys.stderr.write(f"\r  read {n}...")
                sys.stderr.flush()

    sys.stderr.write(f"\r  read {n} lines\n")

    # 只保留：有 2+ 个不同包名的组
    cross_dupes = {}
    for key, items in groups.items():
        pkgs = {p for p, _ in items}
        if len(pkgs) >= 2:
            cross_dupes[key] = items

    total_dupe_files = sum(len(v) for v in cross_dupes.values())

    # 按组大小排序，大的在前
    sorted_dupes = sorted(cross_dupes.items(), key=lambda x: -len(x[1]))

    grouped_by_type = defaultdict(list)
    for (size, seg, ft), items in sorted_dupes:
        grouped_by_type[ft].append({
            "size": size,
            "last_two": seg,
            "file_count": len(items),
            "package_count": len({p for p, _ in items}),
            "packages": sorted({p for p, _ in items}),
            "files": [u for _, u in items],
        })

    result = {
        "summary": {
            "total_entries": n,
            "unique_keys": len(groups),
            "cross_package_groups": len(cross_dupes),
            "cross_package_files": total_dupe_files,
        },
        "groups": dict(grouped_by_type),
    }

    OUTPUT_JSON = "dupes_report.json"
    with open(OUTPUT_JSON, "w") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)

    print(f"Total entries:        {n}")
    print(f"Unique (size,last2):  {len(groups)}")
    print(f"Cross-package groups: {len(cross_dupes)}")
    print(f"Cross-package files:  {total_dupe_files}")
    print(f"-> {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
