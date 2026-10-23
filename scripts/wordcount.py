"""Prose word count of markdown sources (excludes table rows, figure/directive lines, comments, headings markers)."""
import re, sys, glob
def count(path):
    n = 0
    for ln in open(path, encoding="utf-8").read().split("\n"):
        s = ln.strip()
        if not s or s.startswith("|") or s.startswith("![[") or s.startswith("[[") or s.startswith("%"):
            continue
        s = re.sub(r"<!--.*?-->", "", s)
        s = re.sub(r"[#*`]", "", s)
        n += len(s.split())
    return n
if __name__ == "__main__":
    tot = 0
    for p in sys.argv[1:]:
        c = count(p); tot += c; print(f"{c:6d} {p}")
    print(tot, "total")
