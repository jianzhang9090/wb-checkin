#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WorkBuddy 签到值守 · 「一天一轮」总调度（GitHub Actions 版）

一天的语义，严格按一次完整流程执行一次：
  09:00 之后      -> 签到 + 派猫猫去旅行   （当天只做一次）
  旅行途中        -> 每 10 分钟只读巡检一次（不派遣、不重复签到）
  旅行已到达      -> 立即领取旅行礼物      （领取成功即当天全部完成）
  领取完成        -> 当天收工，不再做任何动作，等第二天 09:00

跨轮次的进度记录在 ~/.workbuddy/state.json（由 Actions 缓存在轮次间传递）。
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
STATE_PATH = os.path.join(HOME, ".workbuddy", "state.json")
CST = timezone(timedelta(hours=8))

PY = sys.executable or "python3"


def _now():
    return datetime.now(CST)


def _log(tag, obj):
    print("[%s] %s" % (tag, json.dumps(obj, ensure_ascii=False)))


def _load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            s = json.load(f)
    except Exception:
        s = {}
    today = _now().strftime("%Y-%m-%d")
    if s.get("date") != today:
        s = {"date": today, "daily_done": False, "claimed": False,
             "runs": 0, "last_msg": None}
    return s


def _save_state(s):
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("[state] 写入失败：%s" % e)


def _run(script, args=()):
    """执行子脚本，返回 (退出码, 解析出的 JSON 或 None)。"""
    cmd = [PY, os.path.join(HERE, script)] + list(args)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as e:
        return 1, {"status": "error", "msg": "执行异常：%s" % e}
    out = (p.stdout or "").strip()
    data = None
    if out:
        # 取最后一行能解析成 JSON 的内容作为结构化结果
        for line in reversed(out.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    break
                except Exception:
                    continue
    if p.stdout:
        print(p.stdout.strip())
    if p.stderr:
        print(p.stderr.strip()[:800])
    return p.returncode, data


def main():
    now = _now()
    st = _load_state()
    st["runs"] = st.get("runs", 0) + 1
    hour = now.hour
    failed = False

    print("=" * 60)
    print("北京时间 %s | 第 %s 次巡检 | 签到完成=%s 已领礼物=%s"
          % (now.strftime("%Y-%m-%d %H:%M:%S"), st["runs"],
             st.get("daily_done"), st.get("claimed")))
    print("=" * 60)

    # 1) 09:00 之后：签到 + 派猫猫（一天仅一次）
    if not st.get("daily_done"):
        if hour >= 9:
            print("\n--- 步骤 1：签到 + 派猫猫去旅行 ---")
            rc, data = _run("auto_checkin.py", ["--rt"])
            if rc == 0:
                st["daily_done"] = True
                st["last_msg"] = "签到并派遣完成"
            else:
                failed = True
                st["last_msg"] = "签到/派遣失败，下轮重试"
        else:
            print("\n尚未到 09:00，跳过签到；本轮只做旅行巡检。")
    else:
        print("\n今日签到已完成，跳过。")

    # 2) 旅行巡检：只在未领取礼物时巡检，领取成功即当天收工
    if not st.get("claimed"):
        print("\n--- 步骤 2：旅行巡检（已到达才领取，绝不派遣）---")
        rc, data = _run("travel_keeper.py")
        data = data or {}
        if data.get("status") == "ok":
            st["last_msg"] = data.get("msg")
            if data.get("claimed"):
                st["claimed"] = True
                st["last_msg"] = "已领取旅行礼物（%s 积分），今日全部完成，收工" % (
                    data.get("reward_credit") or "?")
            elif data.get("state") == "traveling":
                st["last_msg"] = "旅行中，等待到达后自动领取"
        else:
            failed = True
            st["last_msg"] = "旅行巡检失败：%s" % (data.get("msg") or "未知原因")
    else:
        print("\n今日礼物已领取，当天任务全部完成，不再做任何动作。")

    _save_state(st)
    print("\n>>> %s" % st.get("last_msg"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
