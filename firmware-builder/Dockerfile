FROM archlinux:latest
ADD mirrorlist /etc/pacman.d
RUN pacman --noconfirm -Syu && pacman --noconfirm -S base-devel rsync bc cpio git wget
RUN useradd -u1000 builder
RUN mkdir /os && chown -R builder:1000 /os
WORKDIR /os

