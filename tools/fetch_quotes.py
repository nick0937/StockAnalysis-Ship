# -*- coding: utf-8 -*-
"""第 1 步：抓行情（Yahoo chart API）＋ 大盤成交金額（證交所 FMTQIK）→ data/raw/
   ★ 移植時不用改；標的來自 config.STOCKS。

   ⚠ 一定要帶正常 User-Agent，否則 Yahoo 回 429、玩股網回 403。
   ⚠ 盤中執行會拿到未完成 K 棒（成交量 0），由 calc_indicators.py 依 BASE_DATE 濾除。
"""
import json, os, sys, time, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import config as C

OUT = os.path.join(BASE, "data", "raw")
os.makedirs(OUT, exist_ok=True)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def get(url, headers=None, tries=4, timeout=30):
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"}
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


syms = [C.INDEX_SYM, C.OTC_SYM] + [C.SYM[c] for c in C.CODES]
print("=" * 84)
for s in syms:
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(s) + "?range=2y&interval=1d")
    try:
        raw = get(url)
    except Exception as e:
        print("%-12s FAIL  %s" % (s, e))
        continue
    open(os.path.join(OUT, s.replace("^", "IDX_") + ".json"), "wb").write(raw)
    d = json.loads(raw)["chart"]["result"][0]
    rows = [(t, c) for t, c in zip(d["timestamp"], d["indicators"]["quote"][0]["close"])
            if c is not None]
    print("%-12s OK  %4d 筆  最後收盤 %.2f" % (s, len(rows), rows[-1][1]))

# ── ★ 補回 Yahoo 大盤序列的缺洞（證交所 TAIEX 官方 OHLC）────────────
# 2026-08-18 踩到：Yahoo 的 ^TWII 在 2026-08-17 整根 K 棒為 null（open/high/low/close
# 全空），calc_indicators.py 會把該日丟掉，於是「前一日收盤」誤用 8/14 的值，
# 大盤漲跌、均線、KD、MACD 連同各檔相對強弱全部失真。個股序列未受影響。
# 對策：用證交所 MI_5MINS_HIST（官方加權指數日 OHLC）逐月補回缺漏日。
def patch_index_gaps():
    fp = os.path.join(OUT, C.INDEX_SYM.replace("^", "IDX_") + ".json")
    if not os.path.exists(fp):
        return
    j = json.loads(open(fp, encoding="utf-8").read())
    r = j["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    ts = r["timestamp"]
    import datetime
    holes = {}
    for n, t in enumerate(ts):
        if q["close"][n] is None:
            holes[datetime.datetime.fromtimestamp(t).strftime("%Y-%m-%d")] = n
    if not holes:
        print("\n大盤序列無缺漏日")
        return
    print("\n★ Yahoo %s 有 %d 個缺漏日：%s → 用證交所官方 OHLC 補值"
          % (C.INDEX_SYM, len(holes), "、".join(sorted(holes))))
    months = sorted({d[:7].replace("-", "") + "01" for d in holes})
    off = {}
    for ym_ in months:
        try:
            d = json.loads(get("https://www.twse.com.tw/rwd/zh/TAIEX/MI_5MINS_HIST"
                               "?date=%s&response=json" % ym_))
            for row in d.get("data", []):
                roc = row[0].split("/")
                ad = "%d-%s-%s" % (int(roc[0]) + 1911, roc[1], roc[2])
                off[ad] = [float(x.replace(",", "")) for x in row[1:5]]
        except Exception as e:
            print("   TAIEX %s FAIL：%s" % (ym_, e))
    fixed, missed = [], []
    for d, n in sorted(holes.items()):
        if d in off:
            o, h, l, c = off[d]
            q["open"][n], q["high"][n], q["low"][n], q["close"][n] = o, h, l, c
            fixed.append("%s 收 %.2f" % (d, c))
        else:
            missed.append(d)
    if fixed:
        open(fp, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
        print("   已補：" + "、".join(fixed))
    if missed:
        print("   ★ 仍缺（證交所也查無，可能是休市日）：" + "、".join(missed))


patch_index_gaps()

# ── 大盤成交金額與股數（證交所 FMTQIK，官方、有整月歷史）──
ym = C.BASE_DATE[:7].replace("-", "") + "01"
try:
    raw = get("https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK?date=%s&response=json" % ym)
    open(os.path.join(OUT, "twse_fmtqik.json"), "wb").write(raw)
    d = json.loads(raw)
    print("\nFMTQIK OK  stat=%s  欄位=%s" % (d.get("stat"), d.get("fields")))
    print("★ 把下列兩行填進 inputs/market.py 的 IDX_AMOUNT / IDX_VOLUME：")
    for row in d.get("data", [])[-3:]:
        roc = row[0].split("/")
        ad = "%d-%s-%s" % (int(roc[0]) + 1911, roc[1], roc[2])
        print('   "%s": %s,   # 成交股數 %s、加權指數 %s'
              % (ad, row[2].replace(",", ""), row[1].replace(",", ""), row[4]))
except Exception as e:
    print("\nFMTQIK FAIL：%s —— 改用玩股網 all-quote-info（id=='0000'）並在 market.py 手填" % e)

print("\n下一步：python calc_indicators.py")
