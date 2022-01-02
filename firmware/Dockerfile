FROM cross-toolchain:latest as toolchain
FROM firmware-builder:latest as builder
COPY --from=toolchain /os/toolchain /os/toolchain

# TODO: try change to armv8-a+crypt+crc and add mtune for cortex.a53+cortex.a57
ENV LFS_ARCH="arm64"
ENV LFS_TARGET="aarch64-unknown-linux-gnu"
ENV LFS_HOST="x86_64-pc-linux-gnu"
ENV PATH="/os/toolchain/bin:$PATH"
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
ADD etc/passwd /os/rootfs/etc
ADD etc/group /os/rootfs/etc

RUN cp /os/toolchain/$LFS_TARGET/lib64/libgcc_s.so.1 /os/rootfs/lib/ && \
    ${LFS_TARGET}-strip /os/rootfs/lib/libgcc_s.so.1

RUN mkdir /tmp/work
WORKDIR /tmp/work

RUN cd /tmp/work && \
    wget https://musl.libc.org/releases/musl-1.2.2.tar.gz && \
    tar -xf musl-1.2.2.tar.gz && \
    mkdir /tmp/work/musl-build && cd /tmp/work/musl-build && \
    ../musl-1.2.2/configure \
    CROSS_COMPILE=$LFS_TARGET- \
    --prefix=/ \
    --disable-static \
    --target=$LFS_TARGET && \
    make -j$(nproc) && \
    DESTDIR=/os/rootfs make install-libs && \
    rm -rf /tmp/work/musl-build && \
    rm -rf /tmp/work/musl-1.2.2 && \
    rm -rf /tmp/work/musl-1.2.2.tar.gz

RUN cd /tmp/work && \
    wget https://busybox.net/downloads/busybox-1.35.0.tar.bz2 && \
    tar -xf busybox-1.35.0.tar.bz2 && \
    cd /tmp/work/busybox-1.35.0 && \
    make ARCH=$LFS_ARCH defconfig && \
    sed -i 's/\(CONFIG_\)\(.*\)\(INETD\)\(.*\)=y/# \1\2\3\4 is not set/g' .config && \
    sed -i 's/\(CONFIG_IFPLUGD\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_FEATURE_WTMP\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_FEATURE_UTMP\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_UDPSVD\)=y/# \1 is not set/' .config && \
    sed -i 's/\(CONFIG_TCPSVD\)=y/# \1 is not set/' .config && \
    make -j$(nproc) ARCH=$LFS_ARCH CROSS_COMPILE="${LFS_TARGET}-" && \
    make ARCH=$LFS_ARCH CROSS_COMPILE="${LFS_TARGET}-" CONFIG_PREFIX="/os/rootfs" install && \
    cp examples/depmod.pl /os/toolchain/bin && \
    chmod 755 /os/toolchain/bin/depmod.pl

ADD etc/protocols /os/rootfs/etc
ADD etc/services /os/rootfs/etc

ADD nanopi-r4s.patch /tmp
ADD kernel-config /tmp
RUN cd /tmp/work && \
    git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git --depth 1 \
              -b linux-5.15.y kernel && \
    cd /tmp/kernel && git apply /tmp/nanopi-r4s.patch && \
    mv /tmp/kernel-config /tmp/work/kernel && \
    make ARCH=$LFS_ARCH CROSS_COMPILE="${LFS_TARGET}-" -j$(nproc) V=1

# TODO: install kernel
# TODO: install init scripts
# TODO: install lightweight ssh server
# TODO: set root password
# TODO: expirt firmware tarballs as artifacts
