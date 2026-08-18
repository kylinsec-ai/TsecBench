# TsecBench

## Kali Headless 环境

### 环境要求

- Docker
- Docker Compose v2

### 构建镜像

```bash
docker compose build
```

`Dockerfile` 基于 `kalilinux/kali-rolling` 构建镜像，使用清华 Kali HTTP 源，并安装 `kali-linux-headless`。

### 启动容器

```bash
docker compose up -d
```

查看运行状态：

```bash
docker compose ps
```

### 进入 Kali

```bash
docker compose exec -it kali bash
```

### 数据持久化

命名卷 `kali-data` 挂载到容器内的 `/workspace`，容器退出或重启后数据仍会保留。

### 停止与重启

停止容器但保留数据：

```bash
docker compose stop
```

重新启动：

```bash
docker compose start
```

重新构建并启动：

```bash
docker compose up -d --build
```

不要使用以下命令删除数据卷：

```bash
docker compose down -v
```
