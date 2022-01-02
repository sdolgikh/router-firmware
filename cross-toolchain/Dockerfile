FROM firmware-builder:latest as builder

ENV CLFS_TARGET=aarch64-unknown-linux-gnu
ENV CLFS_ARCH=arm64
ENV PATH="/os/toolchain/bin:$PATH"
ENV CLFS_ARM_ARCH="armv8-a+crypto+crc"
ENV CLFS_FLOAT="soft"
ENV CLFS_FPU=""

RUN mkdir /os/work && \
    mkdir -p /os/toolchain/$CLFS_TARGET && \
    ln -sfv . /os/toolchain/$CLFS_TARGET/usr
WORKDIR /os/work

ADD nanopi-r4s.patch /tmp
RUN cd /tmp && \
    git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git --depth 1 \
              -b linux-5.15.y kernel && \
    cd /tmp/kernel && git apply /tmp/nanopi-r4s.patch && \
    make ARCH=$CLFS_ARCH INSTALL_HDR_PATH=/os/toolchain/$CLFS_TARGET headers_install

RUN cd /os/work && \
    wget https://mirror.yandex.ru/mirrors/gnu/binutils/binutils-2.37.tar.xz && \
    tar -xf /tmp/binutils-2.37.tar.xz && rm -rf /tmp/binutils-2.37.tar.xz && \
    mkdir /os/work/binutils-build && cd /os/work/binutils-build && \
    ../binutils-2.37/configure \
	--prefix=/os/toolchain \
	--target=${CLFS_TARGET} \
	--with-sysroot=/os/toolchain/${CLFS_TARGET} \
	--disable-nls \
	--disable-multilib && \
    make configure-host && \
    make -j$(nproc) && \
    make install && rm -rf /os/work/binutils-build

RUN cd /os/work && \
    wget https://mirror.yandex.ru/mirrors/gnu/gcc/gcc-11.2.0/gcc-11.2.0.tar.xz && \
    wget https://mirror.yandex.ru/mirrors/gnu/mpfr/mpfr-4.1.0.tar.xz && \
    wget https://mirror.yandex.ru/mirrors/gnu/mpc/mpc-1.2.1.tar.gz && \
    wget https://mirror.yandex.ru/mirrors/gnu/gmp/gmp-6.2.1.tar.xz && \
    tar -xf gcc-11.2.0.tar.xz && \
    tar -xf mpfr-4.1.0.tar.xz && \
    tar -xf mpc-1.2.1.tar.gz && \
    tar -xf gmp-6.2.1.tar.xz && \
    mv mpfr-4.1.0 gcc-11.2.0/mpfr && \
    mv mpc-1.2.1 gcc-11.2.0/mpc && \
    mv gmp-6.2.1 gcc-11.2.0/gmp && \
    mkdir /os/work/gcc-build && cd /os/work/gcc-build && \
    ../gcc-11.2.0/configure --prefix=/os/toolchain \
       --build=x86_64-pc-linux-gnu \
       --host=x86_64-pc-linux-gnu \
       --target=$CLFS_TARGET \
       --with-sysroot=/os/toolchain/$CLFS_TARGET \
       --disable-nls \
       --disable-shared \
       --without-headers \
       --with-newlib \
       --disable-decimal-float \
       --disable-libgomp \
       --disable-libmudflap \
       --disable-libssp \
       --disable-libatomic \
       --disable-libquadmath \
       --disable-threads \
       --enable-languages=c \
       --disable-multilib \
       --with-mpfr-include=$(pwd)/../gcc-11.2.0/mpfr/src \
       --with-mpfr-lib=$(pwd)/mpfr/src/.lib \
       --with-arch=$CLFS_ARM_ARCH && \
    make -j$(nproc) all-gcc all-target-libgcc && \
    make install-gcc install-target-libgcc && rm -rf /os/work/gcc-build

RUN cd /os/work && \
    wget https://musl.libc.org/releases/musl-1.2.2.tar.gz && \
    tar -xf musl-1.2.2.tar.gz && \
    mkdir /os/work/musl-build && cd /os/work/musl-build && \
    ../musl-1.2.2/configure \
      CROSS_COMPILE=$CLFS_TARGET- \
        --prefix=/ \
        --target=$CLFS_TARGET && \
    make -j$(nproc) && \
    DESTDIR=/os/toolchain/$CLFS_TARGET make install && \
    rm -rf /os/work/musl-build && \
    rm -rf /os/work/musl-1.2.2

RUN mkdir /os/work/gcc-build && \
    cd /os/work/gcc-build && \
    ../gcc-11.2.0/configure \
      --prefix=/os/toolchain \
      --build=x86_64-pc-linux-gnu \
      --host=x86_64-pc-linux-gnu \
      --target=$CLFS_TARGET \
      --with-sysroot=/os/toolchain/$CLFS_TARGET \
      --disable-nls \
      --enable-languages=c \
      --enable-c99 \
      --enable-long-long \
      --disable-libmudflap \
      --disable-multilib \
      --with-mpfr-include=$(pwd)/../gcc-11.2.0/mpfr/src \
      --with-mpfr-lib=$(pwd)/mpfr/src/.lib \
      --with-arch=$CLFS_ARM_ARCH && \
    make -j$(nproc) && \
    make install && rm -rf /os/work/gcc-build

FROM scratch
COPY --from=builder /os/toolchain /os/toolchain
