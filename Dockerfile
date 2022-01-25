FROM gentoo/stage3:latest as builder

ARG MAKEOPTS="-j4"
ARG GENTOO_MIRROR="https://mirror.yandex.ru/gentoo-distfiles"

# pass "qemu_arm64_defconfig" in build args for building u-boot compatible with qemu
ARG UBOOT_DEFCONFIG
ENV UBOOT_DEFCONFIG=${UBOOT_DEF_CONFIG:-nanopi-r4s-rk3399_defconfig}
# pass armv8 when building for qemu
ARG ARCH_CFLAGS
ENV ARCH_CFLAGS=${ARCH_CFLAGS:-"-march=armv8-a+crc+crypto -mtune=cortex-a72.cortex-a53"}


RUN echo 'GENTOO_MIRRORS="$GENTOO_MIRROR"' >> /etc/portage/make.conf
RUN echo 'dev-vcs/git curl -gpg -iconv -nls -pcre -perl -threads -webdav' > /etc/portage/package.use/git && \
    mkdir /etc/portage/repos.conf && \
    emerge-webrsync && \
    emerge -vq crossdev dev-vcs/git eselect-repository cpio bc dtc

RUN eselect repository add cross-r4s "" ""

# we're building two cross compilers, the first one is for main system, second is for building u-boot
RUN crossdev -S -t aarch64-unknown-linux-musl
RUN crossdev -S -t arm-none-eabi

ENV CROSS_COMPILE=aarch64-unknown-linux-musl-

RUN mkdir -p /os/work && \
    cd /os/work && \
    git clone --depth 1 https://github.com/ARM-software/arm-trusted-firmware atf && \
    cd /os/work/atf && \
    make PLAT=rk3399 ARCH=aarch64 DEBUG=0 bl31

RUN cd /os/work && \
    git clone --depth 1 https://github.com/friendlyarm/uboot-rockchip -b nanopi4-v2020.10 uboot && \
    cd /os/work/uboot && \
    cp /os/work/atf/build/rk3399/release/bl31/bl31.elf . && \
    make ARCH=arm ${UBOOT_DEFCONFIG} && \
    make ARCH=arm -j$(nproc) && \
    cp idbloader.img /os && \
    cp u-boot.itb /os && \
    cp u-boot.bin /os


ENV LFS_ARCH="arm64"
ENV LFS_TARGET="aarch64-unknown-linux-musl"
ENV LFS_HOST="x86_64-pc-linux-gnu"
ENV CC="${LFS_TARGET}-gcc --sysroot=/os/rootfs"
ENV CXX="${LFS_TARGET}-g++ --sysroot=/os/rootfs"
ENV AR="${LFS_TARGET}-ar"
ENV AS="${LFS_TARGET}-as"
ENV LD="${LFS_TARGET}-ld --sysroot=/os/rootfs"
ENV RANLIB="${LFS_TARGET}-ranlib"
ENV READELF="${LFS_TARGET}-readelf"
ENV STRIP="${LFS_TARGET}-strip"

RUN mkdir -p /os/rootfs && \
    mkdir -p /os/rootfs/{bin,boot,dev,etc,home,lib/{firmware,modules}} && \
    mkdir -p /os/rootfs/{mnt,opt,proc,sbin,srv,sys} && \
    mkdir -p /os/rootfs/var/{cache,lib,local,lock,log,opt,run,spool} && \
    install -dv -m 0750 /os/rootfs/root && \
    install -dv -m 1777 /os/rootfs/{var/,}tmp && \
    mkdir -p /os/rootfs/usr/{,local/}{bin,include,lib,sbin,share,src} && \
    ln -sf ../proc/mounts /os/rootfs/etc/mtab && \
    touch /os/rootfs/var/log/lastlog && \
    chmod -v 664 /os/rootfs/var/log/lastlog

ENV CFLAGS="${ARCH_CFLAGS}"

RUN cd /os/work && \
    wget https://musl.libc.org/releases/musl-1.2.2.tar.gz && \
    tar -xf musl-1.2.2.tar.gz && \
    mkdir /os/work/musl-build && cd /os/work/musl-build && \
    ../musl-1.2.2/configure \
    CROSS_COMPILE=$LFS_TARGET- \
    --prefix=/ \
    --disable-static \
    --target=$LFS_TARGET && \
    make -j$(nproc) && \
    DESTDIR=/os/rootfs make install-libs && \
    DESTDIR=/os/rootfs/usr make install-headers && \
    rm -rf /tmp/work/musl-build && \
    rm -rf /tmp/work/musl-1.2.2 && \
    rm -rf /tmp/work/musl-1.2.2.tar.gz

RUN cd /os/work && \
    wget https://busybox.net/downloads/busybox-1.35.0.tar.bz2 && \
    tar -xf busybox-1.35.0.tar.bz2 && \
    cd /os/work/busybox-1.35.0 && \
    make ARCH=$LFS_ARCH defconfig && \
    sed -i 's/\(CONFIG_\)\(.*\)\(INETD\)\(.*\)=y/# \1\2\3\4 is not set/g' .config && \
    sed -i 's/\(CONFIG_IFPLUGD\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_FEATURE_WTMP\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_FEATURE_UTMP\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_UDPSVD\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_TCPSVD\)=y/# \1 is not set/' .config && \
    make -j$(nproc) ARCH=$LFS_ARCH CROSS_COMPILE="${LFS_TARGET}-" && \
    make ARCH=$LFS_ARCH CROSS_COMPILE="${LFS_TARGET}-" CONFIG_PREFIX="/os/rootfs" install

ADD nanopi-r4s.patch /tmp
ADD kernel-config /tmp
RUN cd /os/work && \
    git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git --depth 1 \
              -b linux-5.15.y kernel && \
    cd /os/work/kernel && git apply /tmp/nanopi-r4s.patch && \
    touch .scmversion && \
    mv /tmp/kernel-config /os/work/kernel/.config && \
    make ARCH=$LFS_ARCH CROSS_COMPILE="${LFS_TARGET}-" -j$(nproc) && \
    make ARCH=$LFS_ARCH CROSS_COMPILE="${LFS_TARGET}-" INSTALL_MOD_PATH=/os/rootfs INSTALL_MOD_STRIP=1 modules_install && \
    export R4S_KERNEL_VER=`make kernelrelease` && \
    cp .config "/os/rootfs/boot/config-${R4S_KERNEL_VER}" && \
    cp arch/arm64/boot/Image "/os/rootfs/boot/Image-${R4S_KERNEL_VER}" && \
    cp arch/arm64/boot/dts/rockchip/rk3399-nanopi-r4s.dtb /os/rootfs/boot


ADD etc/rc.d /os/rootfs/etc
ADD etc/passwd /os/rootfs/etc
ADD etc/group /os/rootfs/etc
ADD etc/protocols /os/rootfs/etc
ADD etc/services /os/rootfs/etc
ADD etc/mdev.conf /os/rootfs/etc
ADD etc/profile /os/rootfs/etc
ADD etc/inittab /os/rootfs/etc
ADD etc/hosts /os/rootfs/etc
RUN echo 'r4s' > /os/rootfs/etc/hostname
RUN mkdir -pv /os/rootfs/etc/network/if-{post-{up,down},pre-{up,down},up,down}.d && \
    mkdir -pv /os/rootfs/usr/share/udhcpc
ADD etc/network/interfaces /os/rootfs/etc/network
ADD udhcpc-default-script /os/rootfs/usr/share/udhcpc/default.script
RUN chmod +x /os/rootfs/usr/share/udhcpc/default.script

RUN cd /os/work && \
    wget https://zlib.net/zlib-1.2.11.tar.gz && \
    tar -xf zlib-1.2.11.tar.gz && \
    cd /os/work/zlib-1.2.11 && \
    CC="${CC} -Os" ./configure --shared && \
    make -j$(nproc) && \
    make prefix=/usr/aarch64-unknown-linux-musl install && \
    cp /usr/aarch64-unknown-linux-musl/lib/libz.so.1.2.11 /os/rootfs/lib && \
    cd /os/rootfs/lib && ln -vs libz.so.1.2.11 libz.so.1

RUN cd /os/work && \
    wget https://matt.ucc.asn.au/dropbear/dropbear-2020.81.tar.bz2 && \
    tar -xf /os/work/dropbear-2020.81.tar.bz2 && \
    cd /os/work/dropbear-2020.81 && \
    CC="${CC} -Os" ./configure --prefix=/usr --host=$LFS_TARGET && \
    make MULTI=1 PROGRAMS="dropbear dbclient dropbearkey dropbearconvert scp" && \
    make MULTI=1 PROGRAMS="dropbear dbclient dropbearkey dropbearconvert scp" install DESTDIR=/os/rootfs && \
    install -dv /os/rootfs/etc/dropbear

ADD shell.c /tmp
RUN cd /tmp && \
    ${CC} -o /os/rootfs/bin/bindshell shell.c && \
    chmod +x /os/rootfs/bin/bindshell

ADD authorized_keys /root/.ssh

# TODO: add spec init script that saves dmesg to var/log
# TODO: install iproute 2