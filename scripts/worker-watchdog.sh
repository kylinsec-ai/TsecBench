#!/usr/bin/env bash
# TSecBench worker 守护进程
# 职责：worker 容器健康检查失败（心跳超时 / 进程僵死）时强制重启
# 用法: bash scripts/worker-watchdog.sh   (常驻；由 start.sh/run.sh 拉起)
#
# 三层保障总览:
#   1. pi_agent.py 会话级看门狗: 子进程无输出 PI_STALL_TIMEOUT 秒 → 杀会话重试
#   2. driver 独立心跳线程: 进程存活即心跳新鲜 (healthcheck = 进程存活)
#   3. 本脚本: unhealthy 超过阈值 → docker restart（最后防线）

INTERVAL="${WATCHDOG_INTERVAL:-30}"          # 检查间隔（秒）
UNHEALTHY_BEFORE_RESTART="${UNHEALTHY_BEFORE_RESTART:-2}"  # 连续 N 次 unhealthy 才重启，避免误杀
HEARTBEAT_MAX_AGE="${HEARTBEAT_MAX_AGE:-300}" # 心跳文件最大年龄（秒）

log() { echo "[$(date '+%F %T')] watchdog: $*"; }

declare -A strikes

while true; do
  for w in tsecbench-worker-1 tsecbench-worker-2 tsecbench-worker-3; do
    state=$(docker inspect --format '{{.State.Status}}' "$w" 2>/dev/null) || continue
    if [ "$state" != "running" ]; then
      # 优雅退出（exit 0 = 任务结束/熔断上限）→ 不拉起，避免无限重启循环
      exit_code=$(docker inspect --format '{{.State.ExitCode}}' "$w" 2>/dev/null)
      if [ "$exit_code" = "0" ]; then
        strikes[$w]=0
        continue
      fi
      # 异常退出（非 0）→ 直接拉起
      log "$w 异常退出(state=$state, exit=$exit_code) — 拉起"
      docker start "$w" 2>/dev/null || docker restart "$w" 2>/dev/null
      strikes[$w]=0
      continue
    fi
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$w" 2>/dev/null)

    # 启动期（health=starting/none，docker 的 start_period 内）不干预，
    # 避免 driver 尚未写心跳文件时被误杀
    if [ "$health" = "starting" ] || [ "$health" = "none" ]; then
      strikes[$w]=0
      continue
    fi

    # 心跳文件年龄（容器内 /tmp/driver_heartbeat）
    age=0
    age=$(docker exec "$w" sh -c 's=$(stat -c %Y /tmp/driver_heartbeat 2>/dev/null); [ -n "$s" ] && echo $(( $(date +%s) - s ))' 2>/dev/null || echo 0)

    unhealthy=0
    if [ "$health" = "unhealthy" ]; then unhealthy=1; fi
    # healthy 但心跳异常过期（进程僵死但 healthcheck 尚未标记）也视为卡死
    if [ "$health" = "healthy" ] && [ "$age" -gt "$HEARTBEAT_MAX_AGE" ] 2>/dev/null; then unhealthy=1; fi

    if [ "$unhealthy" = "1" ]; then
      strikes[$w]=$(( ${strikes[$w]:-0} + 1 ))
      if [ "${strikes[$w]}" -ge "$UNHEALTHY_BEFORE_RESTART" ]; then
        log "$w 卡死(health=$health, 心跳${age}s前) 连续${strikes[$w]}次 — 强制重启"
        docker restart "$w" 2>/dev/null && log "$w 已重启"
        strikes[$w]=0
      else
        log "$w unhealthy #${strikes[$w]}（等待确认）"
      fi
    else
      strikes[$w]=0
    fi
  done
  sleep "$INTERVAL"
done