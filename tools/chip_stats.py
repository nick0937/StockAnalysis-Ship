# -*- coding: utf-8 -*-
"""依 10 日／13 週完整籌碼算出評分所需的客觀統計（守則第 6 節末段）
   ★ 移植時不用改。評分前先跑這支，不要只看最近 3~4 日。
"""
import json, os, sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "inputs"))
import config as C
from chips import out as CHIP

IND = json.load(open(os.path.join(BASE, "data", "indicators.json"), encoding="utf-8"))


def f(x):
    try:
        return float(str(x).replace("%", ""))
    except Exception:
        return None


S = {}
print("=" * 120)
for c in C.CODES:
    v, name = CHIP[c], C.NAME[c]
    inst = v["inst"]
    tot = [f(r[6]) or 0 for r in inst]
    fore = [f(r[1]) or 0 for r in inst]
    ing = [f(r[3]) or 0 for r in inst]
    # 外資持股比重：取最新「有值」的一列與最舊一列比較（8/12 常尚未更新）
    fr = [f(r[11]) for r in inst if f(r[11]) is not None]
    fr_now, fr_old = (fr[0], fr[-1]) if fr else (None, None)
    mn, mg, cc = v["main"], v["margin"], v["conc"]
    m10 = sum(f(r[2]) or 0 for r in mn)
    h10 = sum(f(r[3]) or 0 for r in mn)
    mar10 = sum(x for x in (f(r[2]) for r in mg) if x is not None)
    sh = [f(r[5]) for r in mg if f(r[5]) is not None]

    S[c] = dict(
        sum10=sum(tot), buy_days=sum(1 for x in tot if x > 0),
        f10=sum(fore), i10=sum(ing), s4=sum(tot[:4]), s6=sum(tot[4:]),
        fr_now=fr_now, fr_old=fr_old,
        m10=m10, h10=h10, c5=f(mn[0][4]), c20=f(mn[0][5]), c5_ago=f(mn[4][4]),
        mar10=mar10, sh_now=sh[0] if sh else None, sh_old=sh[-1] if sh else None,
        big_now=f(cc[0][1]), big_4w=f(cc[4][1]), big_13w=f(cc[12][1]),
        fh_now=f(cc[0][2]), fh_13w=f(cc[12][2]),
        ih_now=f(cc[0][3]), ih_13w=f(cc[12][3]), thr=v["conc_threshold"])
    s = S[c]
    print("%s %-8s 法人 10 日合計%+8.0f 張（買超 %d/10 日）｜外資%+8.0f 投信%+7.0f｜"
          "近4日%+8.0f vs 前6日%+8.0f" % (c, name, s["sum10"], s["buy_days"],
                                       s["f10"], s["i10"], s["s4"], s["s6"]))
    print("     %-8s 外資持股比重 %s%% → %s%%（%s pp）｜主力 10 日%+8.0f｜家數差合計%+6.0f"
          % ("", s["fr_old"], s["fr_now"],
             "%+.2f" % (s["fr_now"] - s["fr_old"]) if s["fr_now"] and s["fr_old"] else "n/a",
             s["m10"], s["h10"]))
    print("     %-8s 5日集中度 %s%%（5日前 %s%%）｜20日 %s%%｜融資 10 日%+7.0f｜券資比 %s%%→%s%%"
          % ("", s["c5"], s["c5_ago"], s["c20"], s["mar10"], s["sh_old"], s["sh_now"]))
    print("     %-8s 大戶(%s) 13週前 %.2f%% → 4週前 %.2f%% → 最新 %.2f%%（13週%+.2f、4週%+.2f pp）"
          % ("", s["thr"], s["big_13w"], s["big_4w"], s["big_now"],
             s["big_now"] - s["big_13w"], s["big_now"] - s["big_4w"]))
    print("     %-8s 大戶表內 外資 %.2f%%→%.2f%%（%+.2f）｜投信 %.2f%%→%.2f%%（%+.2f）"
          % ("", s["fh_13w"], s["fh_now"], s["fh_now"] - s["fh_13w"],
             s["ih_13w"], s["ih_now"], s["ih_now"] - s["ih_13w"]))
    print("-" * 120)

json.dump(S, open(os.path.join(BASE, "data", "chip_stats.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("已寫入 data/chip_stats.json")
