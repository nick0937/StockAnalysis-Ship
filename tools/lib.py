# -*- coding: utf-8 -*-
"""共用工具：數字格式化、漲跌配色、sparkline、表格包裝、分數標籤
   ★ 移植時不用改這個檔案。"""
import math
import config as C


# ── 數字格式化 ──────────────────────────────────────────────────
def n(v, d=2):
    """一般數值：>=1000 加千分位，None → 查無"""
    if v is None:
        return "查無"
    return "{:,.{}f}".format(v, d) if abs(v) >= 1000 else "{:.{}f}".format(v, d)


def cm(v, d=0):
    """一律加千分位"""
    return "查無" if v is None else "{:,.{}f}".format(v, d)


def sgn(v, d=2, pct=False):
    """帶正負號，pct=True 補上 %"""
    if v is None:
        return "查無"
    return ("%+." + str(d) + "f") % v + ("%" if pct else "")


def cls(v):
    """漲跌配色 class：紅漲、綠跌、平"""
    if v is None:
        return ""
    return "up" if v > 0 else ("dn" if v < 0 else "flat")


def num_td(v, colored=False, d=None):
    """表格數字格，'--' 與 None 原樣顯示不上色"""
    if v in (None, "--", ""):
        return '<td class="num">--</td>'
    txt = v if d is None else n(float(v), d)
    if colored:
        return '<td class="num %s">%s</td>' % (cls(float(str(v).rstrip("%"))), txt)
    return '<td class="num">%s</td>' % txt


# ── 分數 ────────────────────────────────────────────────────────
def band_of(sc):
    for lo, name in C.BANDS:
        if sc >= lo:
            return name
    return C.BANDS[-1][1]


def scls(sc):
    """分數條 class"""
    return "s70" if sc >= 70 else ("s55" if sc >= 55 else ("s45" if sc >= 45 else "s00"))


def half_up(x):
    """★ 一律用 floor(x+0.5) 半進位，不要用 Python 內建 round 的銀行家捨入"""
    return int(math.floor(x + 0.5))


def total_score(five):
    """five = (籌碼, 技術, 基本, 大盤, 消息)"""
    return half_up(sum(v * w for v, (_, _, w) in zip(five, C.WEIGHTS)))


def market_score(env_score, rs):
    """大盤面分 = 大盤環境分 × 50% + RS 分 × 50%（不主觀給分）"""
    return half_up(env_score * .5 + rs * .5)


# ── 技術面客觀加減分（2026-08-19 新增）────────────────────────────
# ★ 只納入「scores.py 手評技術分未涵蓋的新事件」，嚴禁重複計分：
#   - 均線排列／KD／RSI／乖離率／布林／量價配合 已在手評分內判讀 → 一律不計。
#   - DMA 只計「當日交叉」這個離散事件；**不計零軸與 AMA 的位置**，
#     因為位置等同於均線多頭／空頭排列，計了就是把趨勢算兩次
#     （實測會讓最過熱的個股反而加分，方向錯誤）。
#   - MACD 背離採分級衰減而非硬性截斷：轉折確認後訊號會鈍化但不會瞬間失效。
DIV_ADJ = {"頂背離": -6.0, "底背離": 6.0, "隱性頂背離": -3.0, "隱性底背離": 3.0}
DIV_FULL_BARS = 10     # <= 此根數：全權
DIV_HALF_BARS = 20     # <= 此根數：半權；超過則不計分
DMA_CROSS_ADJ = 2.0    # 單組 DMA 當日交叉的加減分
TECH_ADJ_CAP = 10      # 合計封頂，避免單一機械訊號蓋過整體判讀


def tech_adj(a):
    """回傳 (adj, 明細 list)。adj 為整數，範圍 ±TECH_ADJ_CAP。

    MACD 背離：頂／底同時出現時自然相加抵銷（訊號互相衝突＝不給方向）。
    DMA 三組：只看當日是否交叉，每組 ±DMA_CROSS_ADJ。
    """
    items, total = [], 0.0
    for side in ("top", "bottom"):
        h = (a.get("macd_div") or {}).get(side)
        if not h:
            continue
        base = DIV_ADJ.get(h["kind"], 0.0)
        b = h["bars_since"]
        if b <= DIV_FULL_BARS:
            v, tag = base, ""
        elif b <= DIV_HALF_BARS:
            v, tag = base / 2, "半權"
        else:
            items.append("%s（%d 根前，逾 %d 根不計分）" % (h["kind"], b, DIV_HALF_BARS))
            continue
        total += v
        items.append("%s %s%.1f%s" % (h["kind"], "＋" if v >= 0 else "−", abs(v),
                                      ("・" + tag) if tag else ""))
    for key in ("3-6", "6-12", "5-20"):
        d = (a.get("dma") or {}).get(key)
        if not d or d["cross"] == "無":
            continue
        v = DMA_CROSS_ADJ if d["cross"] == "黃金交叉" else -DMA_CROSS_ADJ
        total += v
        items.append("DMA %s %s %s%.0f" % (key, d["cross"],
                                           "＋" if v >= 0 else "−", abs(v)))
    adj = half_up(max(-TECH_ADJ_CAP, min(TECH_ADJ_CAP, total)))
    if abs(total) > TECH_ADJ_CAP:
        items.append("合計 %s%.1f，封頂至 %s%d"
                     % ("＋" if total >= 0 else "−", abs(total),
                        "＋" if adj >= 0 else "−", abs(adj)))
    return adj, items


def rs_score(ex5, ex20, ex60):
    """RS 分 = 50 + clamp(ex5×1.0 + ex20×1.2 + ex60×0.6, -35, +35)，再 clamp 15~85"""
    raw = ex5 * 1.0 + ex20 * 1.2 + ex60 * 0.6
    return max(15.0, min(85.0, 50 + max(-35.0, min(35.0, raw))))


# ── HTML 片段 ───────────────────────────────────────────────────
def spark(seq):
    """seq = [{'d':..,'c':..}, ...]，viewBox 0 0 100 100，y 反轉（最高價在頂）"""
    cs = [x["c"] for x in seq]
    lo, hi = min(cs), max(cs)
    rng = (hi - lo) or 1.0
    pts = " ".join("%.2f,%.2f" % (100.0 * i / (len(cs) - 1), (hi - c) / rng * 100)
                   for i, c in enumerate(cs))
    col = "var(--up)" if cs[-1] >= cs[0] else "var(--dn)"
    return ('<svg class="spk" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
            '<polyline points="%s" fill="none" stroke="%s" stroke-width="1.6" '
            'vector-effect="non-scaling-stroke" stroke-linejoin="round" stroke-linecap="round"/></svg>'
            % (pts, col))


def mc(label, val, k=""):
    """指標格一格"""
    return ('<div class="mc %s"><span class="mcl">%s</span>'
            '<span class="mcv">%s</span></div>' % (k, label, val))


def twrap(inner, extra=""):
    """★ 所有資料表格都必須包在 .twrap 內（可橫向捲動、第一欄 sticky）
       欄位少的表格加 extra='tnarrow'（3 欄再加 'tn3'）避免撐滿整個寬度"""
    return ('<div class="thint">← 可左右滑動 →</div><div class="twrap %s">%s</div>'
            % (extra, inner))


MA_LABEL = [(5, "5日"), (10, "10日"), (20, "月線"),
            (60, "季線"), (120, "半年線"), (240, "年線")]


def mabar(a):
    """六條均線位置條。a 需有 close 與 ma{'5':..,'10':..,...}"""
    ma = a["ma"]
    ups = [k for k, _ in MA_LABEL if ma.get(str(k)) and a["close"] > ma[str(k)]]
    h = ('<div class="mabh">均線位置：站上 <b>%d/%d</b> 條</div><div class="mabs">'
         % (len(ups), len(MA_LABEL)))
    for k, lab in MA_LABEL:
        v = ma.get(str(k))
        if v is None:
            h += '<span class="mab no">%s 查無</span>' % lab
        else:
            h += ('<span class="mab %s">%s %s %s</span>'
                  % ("ok" if a["close"] > v else "no", lab,
                     "✓" if a["close"] > v else "✗", n(v)))
    return h + "</div>"


def chip(cls_, sym, label, big=False):
    return ('<span class="chip %s%s"><i>%s</i>%s</span>'
            % (cls_, " big" if big else "", sym, label))


def opbox(zone_lab, zone, anchor, cond_lab, cond):
    """★ 操作條件盒：價位區間 + 錨點來源 + 觸發條件（守則第 10 節）"""
    return ('<div class="opbox"><span class="aol">%s</span>'
            '<span class="aoz">%s<small>%s</small></span>'
            '<span class="aol">%s</span><span class="aoc">%s</span></div>'
            % (zone_lab, zone, anchor, cond_lab, cond))
