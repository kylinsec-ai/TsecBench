FROM kalilinux/kali-rolling

RUN rm -f /etc/apt/sources.list.d/* \
    && printf '%s\n' 'deb http://mirrors.tuna.tsinghua.edu.cn/kali kali-rolling main contrib non-free non-free-firmware' > /etc/apt/sources.list \
    && apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y kali-linux-headless \
    && rm -rf /var/lib/apt/lists/*

CMD ["tail", "-f", "/dev/null"]
