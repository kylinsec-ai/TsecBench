---
description: 验证并提交发现的 flag
argument-hint: "<flag值>"
---
验证并准备提交 flag: $1
检查清单：
1. flag 格式是否正确 (flag{...})
2. flag 来源是否为真实命令输出（非模型猜测）
3. 将 flag 写入 FLAG 文件: `echo "$1" > FLAG`
