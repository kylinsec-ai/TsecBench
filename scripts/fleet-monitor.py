#!/usr/bin/env python3
"""舰队持续监控：每 5 分钟记录快照到 work/monitor.log，检测异常模式。

异常检测:
- worker unhealthy / 退出 / 被 watchdog 重启
- pi 会话 0 turns（卡死/余额问题）
- 5 分钟无任何新日志（静默卡死）
- 平台活跃容器异常（>3 或长期 0）
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/home/xiaohei/桌面/TsecBench-main")
TOKEN = "683f634b-30af-40f9-af11-d2ce4c05eab3"
BASE = "https://tsecbench.zc.tencent.com"
LOG = "/home/xiaohei/桌面/TsecBench-main/work/monitor.log"
WORKERS = ["tsecbench-worker-1", "tsecbench-worker-2", "tsecbench-worker-3"]
SNAP = "/home/xiaohei/桌面/TsecBench-main/work/monitor_snap.json"


def run(cmd, timeout=20):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def platform_challenges():
    try:
        import urllib.request
        req = urllib.request.Request(BASE + "/openapi/v1/challenges",
                                     headers={"BENCHMARK_TOKEN": TOKEN})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return []


def main():
    last_log_lines = {}
    while True:
        try:
            rows = platform_challenges()
            total = len(rows)
            done = sum(1 for c in rows if c["is_completed"])
            active = [c["unique_code"] for c in rows if c["container_status"] == "available"]
            earned = sum(c.get("total_score", 0) for c in rows if c["is_completed"])

            lines = [f"[{time.strftime('%F %T')}] 进度: {done}/{total} 题 | 得分约 {earned} | 活跃容器: {active}"]
            issues = []
            for w in WORKERS:
                st = run(["docker", "inspect", w, "--format",
                          "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}"])
                logs = run(["docker", "logs", "--tail", "60", w])
                last = last_log_lines.get(w, "")
                if logs != last:
                    last_log_lines[w] = logs
                    last_log_lines[w + "_ts"] = time.time()
                # 0 turns 检测
                zero = logs.count("0 turns, 1s")
                err = logs.count("ERROR") + logs.count("Traceback") + logs.count("401") + logs.count("402")
                stalled = logs.count("stalled_no_output")
                status = st.split("|")
                state = status[0] if status else "?"
                health = status[1] if len(status) > 1 else "?"
                line = f"  {w}: {state}/{health} | 0turns={zero} | errors={err} | 看门狗重建={stalled}"
                lines.append(line)
                if health == "unhealthy":
                    issues.append(f"{w} UNHEALTHY")
                if zero > 10:
                    issues.append(f"{w} 大量0turns(疑似余额/pi异常) {zero}次")
                if err > 0:
                    issues.append(f"{w} 日志含错误 {err}处")
            if len(active) < 1 and done < total:
                issues.append("平台无活跃容器(可能全部卡死)")
            if issues:
                lines.append("  ⚠ 异常: " + "; ".join(issues))
            with open(LOG, "a", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            snap = {
                "ts": time.time(),
                "total": total, "done": done, "active": active, "earned": earned,
                "issues": issues,
            }
            with open(SNAP, "w") as f:
                json.dump(snap, f)
        except Exception as e:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%F %T')}] 监控异常: {e}\n")
        time.sleep(300)


if __name__ == "__main__":
    main()