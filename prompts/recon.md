---
description: 对目标进行全面侦察，发现开放端口、服务和技术栈
argument-hint: "<目标地址>"
---
对目标 $1 进行全面侦察：
1. 端口扫描: `nmap -sV -sC $1 -p 1-10000 --min-rate 3000`
2. Web 指纹: `whatweb http://$1` (如果有 HTTP 服务)
3. 目录枚举: `gobuster dir -u http://$1 -w /usr/share/wordlists/common.txt -x php,html,txt,bak`
4. 记录所有发现到 MEMORY.md
