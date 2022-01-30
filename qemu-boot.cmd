# U-Boot bootscript for the nanopi r4s on Gentoo Linux
# Build with: mkimage -C none -A arm -T script -d /boot/boot.cmd /boot/boot.scr

setenv rootdev "/dev/vda2"
# setenv ttyconsole "ttyS2,1500000"
# setenv ttyconsole "ttyAMA0"


setenv consoleargs "earlyprintk=serial,ttyS0 console=ttyS0,9600 console=tty0 ignore_loglevel"
setenv zswapargs "zswap.enabled=1 zswap.compressor=zstd zswap.max_pool_percent=50"

# setenv consoleargs "est console=${ttyconsole} earlyprintk=serial,${ttyconsole} debug loglevel=15"

# setenv rootargs "root=${rootdev} rootwait rootfstype=f2fs rootflags=compress_algorithm=zstd"
setenv rootargs "root=${rootdev} rootfstype=f2fs rootflags=compress_algorithm=zstd"
setenv bootargs "${rootargs} ${consoleargs} ${zswapargs} init=/sbin/init"

echo "Boot script loaded from ${devtype} ${devnum}"

load virtio 0 ${kernel_addr_r} Image
setenv fdt_addr_r 0x40000000
fdt addr ${fdt_addr_r}
printenv
booti ${kernel_addr_r} - ${fdt_addr_r}
