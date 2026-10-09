#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""麦门判官 · 纯度评分引擎（离线可用，无需 MCP Token）

用法:
    python3 judge.py "巨无霸套餐 可乐不加冰 薯条蘸圆筒"
    python3 judge.py --json "你的吃法描述"   # 输出 JSON

纯 stdlib 实现，Python >= 3.8。评分对同一输入是确定性的。
"""

import hashlib
import json
import re
import sys

# 新品识别：律法关键词追不上麦当劳上新速度，
# 未收录的「疑似圣物」按新生圣物处理，赐尝鲜分。
NEW_RELIC_RE = re.compile(r"[一-鿿]{2,8}(?:麦旋风|麦满分|脆汁鸡|鸡腿堡|鸡腿|鸡翅|鸡排|圆筒|肉卷|新地|粥|派|堡)")
NEW_RELIC_BONUS = 2          # 每件新生圣物 +2
NEW_RELIC_CAP = 6            # 单次判决尝鲜分上限，防止堆词刷分
NEW_RELIC_AUTO_MAX_LEN = 60  # 自动识别仅限短供述；长档案（订单史）一律走 --new-relic 庭前查档
NEW_RELIC_REMARK = "律法未载的新生圣物，敢为人先，赐尝鲜分。"

# ---------------------------------------------------------------------------
# 律法条文：关键词 → (分值, 判词)
# 分值为正 = 虔诚加分；为负 = 异端扣分
# ---------------------------------------------------------------------------

PIOUS = [
    ("麦门", 5, "口称麦门，心有圣光。"),
    ("麦门永存", 8, "「麦门永存」四字一出，本庭闻到了信仰的味道。"),
    ("巨无霸", 12, "巨无霸，麦门圣物，三层牛肉即三层虔诚。"),
    ("麦辣鸡腿堡", 10, "麦辣鸡腿堡，正统嫡传，辣得庄严。"),
    ("板烧", 8, "板烧鸡腿堡，不炸不腻，修行之人首选。"),
    ("双层吉士", 7, "双层吉士，双倍芝士即双倍敬意。"),
    ("麦乐鸡", 5, "麦乐鸡配酸辣酱，圣餐礼定式。"),
    ("酸辣酱", 4, "麦乐鸡不蘸酸辣酱等于白来，你懂行。"),
    ("麦旋风", 4, "麦旋风，甜品界的转经筒，每一勺都是螺旋的祈祷。"),
    ("无糖", 3, "圣水换无糖，苦修但不改信仰。"),
    ("薯条蘸", 8, "薯条蘸圆筒/冰淇淋，麦门隐修派的绝学，本庭肃然起敬。"),
    ("圆筒", 3, "甜筒入列，餐后有救赎。"),
    ("1+1", 6, "随心配 1+1，精打细算亦是修行。"),
    ("12元", 5, "穷且益坚，不坠麦门之志。"),
    ("中薯", 4, "中薯，分量恰好的中庸之道。"),
    ("麦麦鸡", 4, "麦麦鸡块出列，圣餐礼定式。"),
    ("板烧不加酱", 6, "板烧去酱还愿意吃，这是苦修士。"),
]

HERETIC = [
    ("去酱", -8, "去酱？麦门厨师的手艺你不要，你只要白肉夹面包。"),
    ("不要酱", -8, "同上，去酱即是去魂。"),
    ("雪碧", -10, "在麦当劳点雪碧？可乐才是圣水，雪碧只是气泡水。"),
    ("兑", -6, "「兑」字一出，本庭眉头一皱……你兑了什么？"),
    ("去冰", -3, "去冰可以理解，但圣水的灵魂折损三成。"),
    ("肯德基", -30, "你来到麦门圣地，却心系隔壁疯四？异端！异端！"),
    ("kfc", -30, "在本庭说这三个字母，是要被拖出去的。"),
    ("疯狂星期四", -15, "疯四文学再好，那也是隔壁的经文。"),
    ("V我50", -12, "V 我 50 是隔壁的咒语，麦门不收。"),
    ("只吃沙拉", -10, "来麦当劳只吃沙拉，图什么？图装修吗？"),
    ("奶茶", -8, "麦门有圣水（可乐），你却自带外道饮品。"),
    ("汉堡拆开", -10, "拆开汉堡重新组装，是对圣餐结构主义的公然挑战。"),
    ("不点薯条", -6, "进麦门不点薯条，如同进庙不上香。"),
]

EASTER_EGGS = [
    ("1024", 10, "程序员节参审，本庭加判 10 分：代码和巨无霸都要有层次。"),
    ("加班", 3, "深夜加班还惦记麦门，此乃红尘中真信徒。"),
    ("宝", 2, "带宝同吃，光大麦门。"),
]

RANKS = [
    (96, "麦门之神", "🪐"),
    (86, "麦门大祭司", "👑"),
    (71, "麦门执事", "⚖️"),
    (51, "麦门信徒", "🍞"),
    (31, "见习信徒", "🌱"),
    (0, "麦门路人", "🚶"),
]


def stable_jitter(text: str, lo: int = -3, hi: int = 3) -> int:
    """同一输入永远产生同一个抖动值，保证纯度分可复现。"""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return lo + digest[0] % (hi - lo + 1)


def detect_new_relics(text: str, matched: set) -> list:
    """识别未被律法收录的新品名：候选名词与已判关键词无重叠才算新圣物。
    仅对短供述启用（长档案里的常规商品不是新品，会造成假阳性）。"""
    if len(text) > NEW_RELIC_AUTO_MAX_LEN:
        return []
    relics = []
    for m in NEW_RELIC_RE.finditer(text):
        relic = re.sub(r"^[加配和带与]+", "", m.group(0)) or m.group(0)
        if len(relic) < 3:
            continue
        if any(kw in relic or relic in kw for kw in matched if kw != "（空白证词）"):
            continue
        if relic not in relics:
            relics.append(relic)
    return relics


def judge(text: str, extra_relics=None) -> dict:
    lowered = text.lower()
    score = 50  # 起始纯度：生而平等，善恶自负
    notes = []
    matched = set()

    for kw, pts, remark in PIOUS + HERETIC + EASTER_EGGS:
        if kw.lower() in lowered:
            matched.add(kw)
            score += pts
            verdict_word = "虔诚" if pts > 0 else "异端"
            notes.append({"evidence": kw, "delta": pts, "kind": verdict_word, "remark": remark})

    # 新生圣物：自动识别 + 庭前查档传入（--new-relic）合并去重。
    # 查档传入的是核验过的新品全名（可能包含已判关键词如「板烧」），故只做精确去重。
    relics = detect_new_relics(text, matched)
    for r in (extra_relics or []):
        if r and r not in relics and not any(r in x or x in r for x in relics):
            relics.append(r)
    for relic in relics[:NEW_RELIC_CAP // NEW_RELIC_BONUS]:
        matched.add(relic)
        score += NEW_RELIC_BONUS
        notes.append({
            "evidence": relic,
            "delta": NEW_RELIC_BONUS,
            "kind": "新生圣物",
            "remark": NEW_RELIC_REMARK,
        })

    if not notes:
        score += 5
        notes.append({
            "evidence": "（空白证词）",
            "delta": 5,
            "kind": "存疑",
            "remark": "你说得太过空灵，本庭啥也没听懂，暂按沉默皈依处理。",
        })

    score += stable_jitter(text)
    score = max(0, min(100, score))

    for threshold, rank, icon in RANKS:
        if score >= threshold:
            final_rank, final_icon, floor = rank, icon, threshold
            break

    return {
        "input": text,
        "purity": score,
        "rank": final_rank,
        "icon": final_icon,
        "rank_floor": floor,
        "notes": notes,
        "closing": CLOSINGS[min(len(CLOSINGS) - 1, score // 20)],
    }


CLOSINGS = [
    "本庭宣判：你与麦门的缘分尚在途中，愿圣水引你归途。",
    "信仰的种子已经发芽，常吃常新，麦门的大门为你敞开。",
    "此等虔诚，麦门大地都将记得你的名字。",
    "本庭宣布当庭释放，并授予你传播麦门福音的资格。",
    "凡人之躯，行神之食。麦门之神在此，众生退散。",
]


def render_verdict(result: dict) -> str:
    lines = []
    lines.append("=" * 46)
    lines.append("    麦门最高裁判所 · 判决书")
    lines.append("=" * 46)
    lines.append(f"被审判的吃法：{result['input']}")
    lines.append("")
    lines.append("【逐条取证】")
    for n in result["notes"]:
        sign = "+" if n["delta"] > 0 else ""
        lines.append(f"  ▸ 「{n['evidence']}」 {sign}{n['delta']}  [{n['kind']}]")
        lines.append(f"      {n['remark']}")
    lines.append("")
    lines.append(f"【麦门纯度】{result['purity']} / 100")
    lines.append(f"【最终段位】{result['icon']} {result['rank']}")
    lines.append("")
    lines.append(f"【结案陈词】{result['closing']}")
    lines.append("")
    lines.append("              麦门！")
    lines.append("=" * 46)
    return "\n".join(lines)


def main() -> int:
    argv = sys.argv[1:]
    as_json = "--json" in argv
    extra_relics = []
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] == "--new-relic" and i + 1 < len(argv):
            extra_relics = [x for x in re.split(r"[,，]", argv[i + 1]) if x]
            i += 2
        elif argv[i] == "--json":
            i += 1
        else:
            rest.append(argv[i])
            i += 1
    if not rest:
        print("用法: judge.py [--json] [--new-relic \"新品1,新品2\"] \"你的麦当劳吃法描述\"", file=sys.stderr)
        return 2
    result = judge(" ".join(rest), extra_relics=extra_relics)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(render_verdict(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
