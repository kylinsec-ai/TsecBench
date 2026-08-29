#!/bin/bash
set -e
cd /home/xiaohei/桌面/tsecbench-platform
PORT=18999 TSECBENCH_CONFIG=/tmp/opencode/local_tasks.json BENCHMARK_TOKEN=local-test-token \
  /tmp/opencode/tsec-venv/bin/python main.py > /tmp/opencode/platform.log 2>&1 &
PLATFORM_PID=$!
sleep 6
python3 - <<'PYEOF'
import sys; sys.path.insert(0, '.')
from adapter.platform_client import PlatformClient
from adapter.config import ControllerConfig
import os
os.environ['ADAPTER_PLATFORM'] = 'generic'
spec = {'vpn_check_url': ''}
pc = PlatformClient('http://127.0.0.1:18999', 'local-test-token', timeout=10, mode='generic', spec=spec)

chs = pc.list_challenges()
print('=== 1. 拉题 ===')
for c in chs:
    print(f'  {c.unique_code} diff={c.difficulty} score={c.total_score} flags={c.flag_count}')

st = pc.start_challenge('local_easy_01')
print('=== 2. start ===', st.container_addr)

r = pc.submit_flag('local_easy_01', 'flag{local_easy_flag}')
print('=== 3. submit 正确 ===', f'correct={r.correct} awarded={r.awarded} prog={r.correct_flag_count}/{r.total_flag_count}')

r2 = pc.submit_flag('local_easy_01', 'flag{local_easy_flag}')
print('=== 4. 重复 ===', f'duplicate={r2.duplicate}')

r3 = pc.submit_flag('local_easy_01', 'flag{wrong}')
print('=== 5. 错误 flag ===', f'correct={r3.correct} awarded={r3.awarded}')

cl = pc.close_challenge('local_easy_01')
print('=== 6. close ===', cl.closed)

ctrl = ControllerConfig.from_env()
print('=== 7. 难度时间盒 ===')
print(f'  easy={ctrl.timebox_for_difficulty("easy")}s medium={ctrl.timebox_for_difficulty("medium")}s hard={ctrl.timebox_for_difficulty("hard")}s unknown={ctrl.timebox_for_difficulty("weird")}s 轮次乘数={ctrl.round_factors}')
print('  ALL OK')
PYEOF
kill $PLATFORM_PID 2>/dev/null
echo "platform stopped"
