#!/usr/bin/env python3
"""递归抓取 https://registry.npmmirror.com/-/binary/ 下所有 type=="file" 的条目，
输出 JSON Lines（每行 {"url":..., "size":...}）到 npmmirror_files.jsonl。

用法:
    python3 fetch_npmmirror.py            # 默认输出 npmmirror_files.jsonl, 32 并发
    python3 fetch_npmmirror.py out.jsonl  # 指定输出文件
    python3 fetch_npmmirror.py out.jsonl 64  # 指定并发数
"""

import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = "https://registry.npmmirror.com/-/binary/"


def fetch(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries - 1:
                sys.stderr.write(f"[ERR] {url}: {e}\n")
                return None
            time.sleep(0.5 * (i + 1))
    return None


def main():
    output = sys.argv[1] if len(sys.argv) > 1 else "npmmirror_files.jsonl"
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 32

    print(f"Root: {ROOT}\nOutput: {output}\nWorkers: {workers}", flush=True)
    entries = fetch(ROOT)
    if not entries:
        sys.exit("Failed to fetch root")

    pending = [e["url"] for e in entries if e.get("type") == "dir"]
    seen = set()
    n_files = 0
    n_dirs = 0
    start = time.time()

    with open(output, "w") as out:
        # root 层的 file
        for e in entries:
            if e.get("type") == "file" and e["url"] not in seen:
                seen.add(e["url"])
                out.write(json.dumps({"url": e["url"], "size": e.get("size")}) + "\n")
                n_files += 1

        with ThreadPoolExecutor(max_workers=workers) as pool:
            while pending:
                batch, pending = pending, []
                futures = {pool.submit(fetch, u): u for u in batch}
                for fut in as_completed(futures):
                    res = fut.result()
                    n_dirs += 1
                    if res is None:
                        continue
                    for e in res:
                        t = e.get("type")
                        u = e.get("url")
                        if not u or u in seen:
                            continue
                        if t == "dir":
                            pending.append(u)
                        elif t == "file":
                            seen.add(u)
                            out.write(json.dumps({"url": u, "size": e.get("size")}) + "\n")
                            n_files += 1
                    if n_dirs % 100 == 0:
                        elapsed = time.time() - start
                        sys.stderr.write(
                            f"\r  dirs={n_dirs} files={n_files} "
                            f"queue={len(pending)} {elapsed:.0f}s"
                        )
                        sys.stderr.flush()
                        out.flush()

    sys.stderr.write("\n")
    print(f"Done. dirs={n_dirs} files={n_files} unique={len(seen)} "
          f"elapsed={time.time()-start:.0f}s -> {output}")


if __name__ == "__main__":
    main()
