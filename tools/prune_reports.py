# -*- coding: utf-8 -*-
"""只保留最新 N 期（預設 10 個開盤日）的報告資料夾，其餘刪除。

守則第 12B 節（2026-08-27 定案，Nick 指定）：
    跑今日／昨日報告之前，先檢查 REPO 底下的 8 位數字資料夾，
    只留最新 N 期，超出的一律先刪除再跑報告。

用法：
    python prune_reports.py            # 實際刪除
    python prune_reports.py --dry-run  # 只列出會刪什麼，不動檔案

★ 安全限制（不要拿掉）：
  1. 只處理 REPO 底下「檔名剛好 8 位數字」的資料夾，live/、tools/ 等一律不碰。
  2. 資料夾內若有 index.html 以外的檔案，<b>不刪、只警告</b>——代表裡面有非產生器產出的東西。
  3. 保留數量由 config.KEEP_PERIODS 決定；本檔不自行決定要留幾期。
  4. 刪除是本機檔案系統操作，git 端要等使用者跑「建立Commit.bat」才會反映到 repo 與 GitHub Pages。
"""
import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
sys.path.insert(0, os.path.join(BASE, "inputs"))
import config as C

KEEP = getattr(C, "KEEP_PERIODS", 10)


def list_periods(repo=None):
    """回傳 REPO 底下所有 8 位數字資料夾，由新到舊。"""
    repo = repo or C.REPO
    return sorted([d for d in os.listdir(repo)
                   if re.fullmatch(r"\d{8}", d) and os.path.isdir(os.path.join(repo, d))],
                  reverse=True)


def prune(dry_run=False, quiet=False, repo=None):
    """刪除最新 KEEP 期以外的報告資料夾。回傳 (已刪, 略過, 保留數)。"""
    repo = repo or C.REPO
    dirs = list_periods(repo)
    keep, drop = dirs[:KEEP], dirs[KEEP:]
    removed, skipped = [], []
    for d in drop:
        p = os.path.join(repo, d)
        extra = [f for f in os.listdir(p) if f != "index.html"]
        if extra:
            skipped.append((d, extra))
            continue
        if not dry_run:
            shutil.rmtree(p)
        removed.append(d)
    if not quiet:
        print("=" * 92)
        print("報告資料夾保留檢查（只留最新 %d 期）" % KEEP)
        print("    現有 %d 期：%s ~ %s" % (len(dirs), dirs[-1] if dirs else "-",
                                          dirs[0] if dirs else "-"))
        if removed:
            print("    %s %d 期：%s"
                  % ("將刪除（--dry-run）" if dry_run else "已刪除", len(removed),
                     "、".join(removed)))
            print("    ★ 刪除只發生在本機；推上 GitHub Pages 要等使用者跑「建立Commit.bat」")
        else:
            print("    無超出保留範圍者，不刪除")
        for d, extra in skipped:
            print("    ⚠ %s 內有 index.html 以外的檔案（%s），未刪除，請人工確認"
                  % (d, "、".join(extra)))
        print("    保留 %d 期：%s" % (len(keep), "、".join(keep)))
    return removed, skipped, len(keep)


if __name__ == "__main__":
    prune(dry_run="--dry-run" in sys.argv)
