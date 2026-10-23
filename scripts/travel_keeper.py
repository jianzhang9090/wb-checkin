#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""云端旅行值守（一天一轮版）

只做两件事：
  1. 读取派猫猫旅行状态；
  2. 若已到达（arrived），立即领取旅行积分。

绝不派遣——每日派遣只由 09:00 的签到任务执行一次，保证一天只派一次。
领取成功后由上层（app.py）记录「今日已完成」，当天不再巡检。
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import rt_auth
import workbuddy_checkin as wc


def _out(obj):
    print(json.dumps(obj, ensure_ascii=False))
    return 0 if obj.get("status") == "ok" else 1


def main():
    rt = rt_auth.read_rt()
    if not rt:
        return _out({"status": "error", "state": None, "claimed": False,
                     "msg": "长效令牌缺失"})

    r = rt_auth.refresh_token(rt)
    if r.get("code") != 0 or not isinstance(r.get("data"), dict):
        return _out({"status": "error", "state": None, "claimed": False,
                     "msg": "令牌刷新失败 code=%s %s"
                            % (r.get("code"), r.get("msg") or "")})
    data = r["data"]
    at = data.get("accessToken") or ""
    new_rt = data.get("refreshToken") or ""
    if not at:
        return _out({"status": "error", "state": None, "claimed": False,
                     "msg": "刷新应答缺少接口令牌"})
    if new_rt and new_rt != rt:
        try:
            rt_auth.save_rt(new_rt, source="refresh")
        except Exception:
            pass

    status = wc._travel_get(at, wc.TRAVEL_STATUS_PATH)
    config = wc._travel_get(at, wc.TRAVEL_CONFIG_PATH)
    if status is None:
        return _out({"status": "error", "state": None, "claimed": False,
                     "msg": "旅行状态查询失败"})

    parsed = wc.parse_travel(status, config)
    state = parsed.get("state")
    out = {"status": "ok", "state": state,
           "location_name": parsed.get("location_name"),
           "remaining_text": parsed.get("remaining_text"),
           "daily_limit_reached": parsed.get("daily_limit_reached"),
           "reward_credit": parsed.get("reward_credit"),
           "claimed": False}

    if state == "arrived":
        res = wc.travel_claim(at)
        if res.get("action") == "claimed":
            out["claimed"] = True
            out["reward_credit"] = res.get("reward_credit") or parsed.get("reward_credit")
            out["msg"] = res.get("message") or "已领取旅行奖励"
        else:
            out["msg"] = "已到达但领取失败：%s（下次巡检重试）" % (res.get("message") or "未知原因")
    elif state == "traveling":
        out["msg"] = "旅行中：%s，还需 %s" % (parsed.get("location_name") or "未知地点",
                                            parsed.get("remaining_text") or "未知")
    elif parsed.get("daily_limit_reached"):
        out["msg"] = "空闲，今日派遣次数已用完（每日派遣由 09:00 任务执行）"
    else:
        out["msg"] = "空闲，今日未派遣（每日派遣由 09:00 任务执行）"
    return _out(out)


if __name__ == "__main__":
    sys.exit(main())
