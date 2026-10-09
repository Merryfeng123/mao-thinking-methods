#!/usr/bin/env python3
"""
mao-thinking-methods 一致性校验

用法：python3 consistency_check.py

检查项：
  1. 垃圾字符（重复词 / 乱码 / 非法占位符 / 编码坏字符）
  2. 党八股表述统一性（原文是六条罪状，不是八条）
  3. 伪引文（标注为「原文/原话」的引用，必须能在原文逐字查到）
  4. 卷次与标题一致性
  5. 链接有效性
  6. 内容厚度（过薄的分章）

退出码：0 = 通过，1 = 有问题
"""
import pathlib, re, json, sys

SK = pathlib.Path(__file__).resolve().parent
CH = SK / "chapters"


def slug(t):
    s = re.sub(r'[：:，,。、（）()《》""\'\s]+', '', t)
    return (re.sub(r'[^一-鿿A-Za-z0-9]+', '-', s)[:20] or "x")


def main():
    if not CH.exists():
        print(f"找不到 chapters/ 目录：{CH}")
        sys.exit(1)

    meta = json.load(open(SK / "meta.json", encoding="utf-8"))
    CN = {1: "一", 2: "二", 3: "三", 4: "四"}

    # 原文全文（用于引文核验）
    arts = {}
    for m in meta:
        p = SK / "arts2" / f"{m['id']:03d}.txt"
        if p.exists():
            arts[m["id"]] = p.read_text(encoding="utf-8")
    full = "\n".join(arts.values())

    issues = []
    md_files = list(SK.glob("*.md")) + list(CH.glob("*.md"))

    # ── 1. 垃圾字符 ────────────────────────────────
    GARBAGE = [
        (r"introductoryintroduction", "英文词重复"),
        (r"\bGgJj\b", "乱码"),
        (r"_invalid", "非法占位符"),
        (r"\uFFFD", "编码坏字符"),
        (r"<!--\s*待", "未完成占位"),
        (r"\bTODO\b", "TODO 残留"),
    ]
    for f in md_files:
        t = f.read_text(encoding="utf-8")
        for pat, label in GARBAGE:
            for m in re.finditer(pat, t):
                line = t[:m.start()].count("\n") + 1
                issues.append(f"[垃圾/{label}] {f.name}:{line}")

    # ── 2. 党八股表述统一性 ───────────────────────
    for f in md_files:
        t = f.read_text(encoding="utf-8")
        if re.search(r"党八股.{0,4}八条|八条.{0,4}党八股|党八股.{0,4}八大特征", t):
            issues.append(f"[过时表述] {f.name}: 党八股应为六大罪状（原文只列六条）")

    # ── 3. 伪引文（只抓明确标注为原文的引用）──────
    QUOTE = re.compile(r"(?:原文|原话|原文语|他说)[：:]\s*「([^」]{8,60})」")
    for f in md_files:
        t = f.read_text(encoding="utf-8")
        for m in QUOTE.finditer(t):
            q = m.group(1)
            if q not in full:
                line = t[:m.start()].count("\n") + 1
                issues.append(f"[伪引文] {f.name}:{line}  「{q}」原文查无此句")

    # ── 4. 卷次 / 标题一致性 ─────────────────────
    for m in meta:
        fn = CH / f"ch{m['id']:03d}-{slug(m['title'])}.md"
        if not fn.exists():
            issues.append(f"[文件缺失] ch{m['id']:03d} {m['title']}")
            continue
        t = fn.read_text(encoding="utf-8")
        if m["title"] not in t.split("\n")[0]:
            issues.append(f"[标题不符] ch{m['id']:03d} 期望「{m['title']}」")
        mm = re.search(r'\*\*卷次\*\*：第([一二三四])卷', t)
        if not mm or mm.group(1) != CN[m["vol"]]:
            issues.append(f"[卷次不符] ch{m['id']:03d} meta={CN[m['vol']]}")

    # ── 5. 链接有效性 ─────────────────────────────
    skill = (SK / "SKILL.md").read_text(encoding="utf-8")
    names = {p.name for p in CH.glob("*.md")}
    for l in re.findall(r'\((chapters/[^)]+)\)', skill):
        if not (SK / l).exists():
            issues.append(f"[死链:SKILL] {l}")
    for f in CH.glob("*.md"):
        for l in re.findall(r'\]\((ch\d+[^)]*\.md)\)', f.read_text(encoding="utf-8")):
            if l not in names:
                issues.append(f"[死链:{f.name}] → {l}")

    # ── 6. 内容厚度 ───────────────────────────────
    for m in meta:
        fn = CH / f"ch{m['id']:03d}-{slug(m['title'])}.md"
        if fn.exists() and len(fn.read_text(encoding="utf-8")) < 800:
            issues.append(f"[过薄] ch{m['id']:03d} {len(fn.read_text(encoding='utf-8'))}字")

    # ── 输出 ─────────────────────────────────────
    print("=" * 64)
    print(f"  一致性校验 · 扫描 {len(md_files)} 个 md 文件 / {len(meta)} 篇")
    print("=" * 64)
    if not issues:
        print("\n  ✅ 全部通过\n")
        sys.exit(0)

    by = {}
    for i in issues:
        by.setdefault(i.split("]")[0] + "]", []).append(i)
    for k, v in sorted(by.items(), key=lambda x: -len(x[1])):
        print(f"\n{k}  × {len(v)}")
        for x in v[:8]:
            print("   ", x)
        if len(v) > 8:
            print(f"    ...另 {len(v) - 8} 条")
    print(f"\n  合计：{len(issues)}\n")
    sys.exit(1)


if __name__ == "__main__":
    main()