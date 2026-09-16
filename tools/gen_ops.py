# -*- coding: utf-8 -*-
"""★ 依 data/indicators.json 自動產生 inputs/shorts.py 的 OPS_S（操作參考）。

守則 §9.2 規定：操作參考的「上方壓力／下方防線」必須把 20／60 日 VWAP、
20 日區間上下緣、未回補缺口、移動停利線一起列進去；第 3 句必須寫出
VWAP 位置、區間位置、乖離 z-score 與移動停利線狀態。

這一段是純數字判讀，手寫容易漏項也容易抄錯，所以改為每期自動產生。
用法：python tools/gen_ops.py（在 calc_indicators.py 之後、build_report.py 之前跑）
"""
import io
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import config as C  # noqa: E402

IND = json.load(io.open(os.path.join(BASE, "data", "indicators.json"),
                        encoding="utf-8"))
SHORTS = os.path.join(BASE, "inputs", "shorts.py")

f2 = lambda x: ("%.2f" % x) if x is not None else "查無"


def ops_text(code):
    a = IND["stocks"][code]
    b, g, at = a["breakout"], a["gap"], a["atr"]
    z = a.get("bias_z") or {}
    md = a["date"][5:].replace("-", "/")
    chg = "平盤" if abs(a["chg_pct"]) < 0.005 else "%+.2f%%" % a["chg_pct"]

    s1 = ("%s 開 %s、高 %s、低 %s、收 %s（%s），成交 %s 張為 20 日均量的 %.2f 倍。"
          % (md, f2(a["open"]), f2(a["high"]), f2(a["low"]), f2(a["close"]), chg,
             format(int(round(a["vol_lots"])), ","), a["vr20"]))

    up, dn = [], []
    for nm, v in (("5 日線", a["ma"]["5"]), ("10 日線", a["ma"]["10"]),
                  ("月線", a["ma"]["20"]), ("季線", a["ma"]["60"]),
                  ("半年線", a["ma"]["120"]), ("年線", a["ma"]["240"]),
                  ("20 日 VWAP", a["vwap20"]), ("60 日 VWAP", a["vwap60"]),
                  ("布林上軌", a["bb_up"]), ("布林下軌", a["bb_dn"]),
                  ("20 日區間頂 %s" % f2(b["hi"]), b["hi"]),
                  ("20 日區間底 %s" % f2(b["lo"]), b["lo"]),
                  ("移動停利線", at["stop"])):
        if v is None:
            continue
        lab = nm if nm.startswith("20 日區間") else "%s %s" % (nm, f2(v))
        (up if v > a["close"] else dn).append(lab)
    for gp in g["open_gaps"]:
        lab = "%s未回補缺口 %s~%s" % (gp["dir"], f2(gp["lo"]), f2(gp["hi"]))
        (up if gp["lo"] > a["close"] else dn).append(lab)
    s2 = ("<b>上方壓力：%s；下方防線：%s。</b>"
          % ("、".join(up) if up else "無（已在所有參考價之上）",
             "、".join(dn) if dn else "無（已在所有參考價之下）"))

    pos = ("區間內 %.0f%% 位置" % b["pos"]) if b.get("pos") is not None else b["dir"]
    s3 = ("<b>K %s→%s、D %s、RSI %s、MACD 柱狀體 %.2f、20 日乖離 %+.2f%%（z %+.2f）、"
          "%%B %.1f；站上均線 %d/6；%s 20 日 VWAP、%s、移動停利線 %s（%s）。</b>"
          % (f2(a["k_prev"]), f2(a["k"]), f2(a["d"]), f2(a["rsi"]), a["osc"],
             a["bias20"], z.get("z", 0), a["pb"],
             sum(1 for k in ("5", "10", "20", "60", "120", "240")
                 if a["close"] >= a["ma"][k]),
             "站上" if a["close"] >= a["vwap20"] else "跌破", pos,
             f2(at["stop"]), "價格仍在其上" if at["above"] else "⚠ 已跌破"))
    return s1, s2, s3


def main():
    lines = ["OPS_S = {"]
    for c in C.CODES:
        s1, s2, s3 = ops_text(c)
        lines.append('"%s": "%s"\n        "%s"\n        "%s",\n' % (c, s1, s2, s3))
    lines.append("}\n")
    block = "\n".join(lines)

    src = io.open(SHORTS, encoding="utf-8").read()
    st = src.index("OPS_S = {")
    en = st + re.search(r"\n\}\n", src[st:]).start() + 3
    io.open(SHORTS, "w", encoding="utf-8", newline="").write(src[:st] + block + src[en:])
    print("OPS_S 已依 %s 收盤自動重寫（%d 檔）" % (IND["idx"]["date"], len(C.CODES)))


if __name__ == "__main__":
    main()
