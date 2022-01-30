import builder.gen
import builder.loopmount
import os
import subprocess
import sys
import fallocate


class BuilderMultistep:

    def __init__(self, build_dir, target):
        self.target = target
        self.build_dir = build_dir
        if not os.path.exists(self.build_dir):
            os.makedirs(self.build_dir)
        suffix = '-qemu' if self.target == 'qemu' else ''
        self.image_name = 'r4s%s:latest' % suffix

    def generate_dockerfile(self):
        gen = builder.gen.DockerfileGen(self.target)
        outfile_path = os.path.join(self.build_dir, 'Dockerfile')
        with open(outfile_path, 'w') as f:
            gen.generate(f)
        return outfile_path

    def build_docker_image(self, dockerfile_path):
        cmd = ['/usr/bin/docker', 'build', '-t', self.image_name, '-f', dockerfile_path, '.']
        subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr, check=True)

    def allocate_image(self):
        image_path = os.path.join(self.build_dir, 'firmware.bin')
        alloc_size = 2*1000*1000*1000  # 2G
        with open(image_path, 'w+b') as f:
            fallocate.fallocate(f, 0, alloc_size)
        return image_path

    def partition_device(self, dev):
        if not dev.startswith('/dev/loop'):
            raise RuntimeError('trying to parted on non-loop partition, dangerous and unexpected!')
        subprocess.run(['dd', 'if=/dev/zero', 'of=%s' % dev, 'bs=1M', 'count=16'], check=True, stdout=sys.stdout,
                       stderr=sys.stderr)
        parted_script = ([
            'mklabel gpt',
            'unit mib mkpart primary 16 128',
            'name 1 boot',
            'unit mib mkpart primary 128 100%',
            'name 2 rootfs',
            'set 1 boot on',
            'unit mib print'
        ])
        for line in parted_script:
            parted_cmd = ['parted', '-s', dev, *(line.split())]
            subprocess.run(parted_cmd, check=True, capture_output=True)
        subprocess.run(['mkfs.ext4', '-L', 'boot', '%sp1' % dev], check=True, capture_output=True)
        subprocess.run(['tune2fs', '-o', 'journal_data_writeback', '%sp1' % dev], check=True, capture_output=True)
        subprocess.run(['mkfs.f2fs', '-l', 'rootfs', '-O', 'extra_attr,inode_checksum,sb_checksum,compression',
                        '%sp2' % dev], check=True, capture_output=True)

    def upload_firmware_to_device(self, blockdev):
        if not blockdev.startswith('/dev/loop'):
            raise RuntimeError('trying to direct write to non-loop partition, dangerous and unexpected!')
        self.save_bootloader_images(blockdev)
        self.export_rootfs(blockdev)

    def save_bootloader_images(self, blockdev):
        if self.target != 'qemu':
            for fname in ['idbloader.img', 'u-boot.itb']:
                out_path = os.path.join(self.build_dir, fname)
                with open(out_path, 'wb') as f:
                    cmd = ['docker', 'run', '--rm', self.image_name, 'cat', '/os/%s' % fname]
                    subprocess.run(cmd, stdout=f, check=True, stderr=sys.stderr)
                seek = 64 if fname == 'idbloader.img' else 16384
                cmd = ['dd', 'if=%s' % out_path, 'of=%s' % blockdev, 'seek=%s' % seek, 'conv=notrunc']
                print(' '.join(cmd))
                subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)
        else:
            out_path = os.path.join(self.build_dir, 'u-boot.bin')
            with open(out_path, 'wb') as f:
                cmd = ['docker', 'run', '--rm', self.image_name, 'cat', '/os/u-boot.bin']
                subprocess.run(cmd, stdout=f, check=True, stderr=sys.stderr)

    def write_fstab(self, out_f, blockdev):
        with subprocess.Popen(['blkid'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            output, errors = p.communicate()
            if p.returncode != 0:
                print(errors)
                raise RuntimeError('blkid failed')
            output = output.decode('utf-8')
            uuids = {}
            print(output)
            for row in output.split('\n'):
                row = row.strip()
                if not len(row):
                    continue
                cols = row.split()
                dev_name = cols[0].rstrip(':')
                uuid = None
                for col in cols:
                    if col.startswith('UUID'):
                        uuid = col.split('"')[1]
                if uuid is not None:
                    uuids[dev_name] = uuid

        rootfs_dev = '%sp2' % blockdev
        bootfs_dev = '%sp1' % blockdev
        out_f.write('UUID="%s"\t/\tf2fs\tdefaults,nobarrier,noatime,nodiratime,compress_algorithm=zstd,compress_extension=*\t0 1\n' % uuids[rootfs_dev])
        out_f.write('UUID="%s"\t/boot\text4\tdefaults,noauto,noatime,nodiratime,commit=600,errors=remount-ro\t0 2\n' % uuids[bootfs_dev])
        out_f.write('tmpfs\ttmp\ttmpfs\tdefaults,nosuid\n')

    def export_vmlinux(self):
        file_path = os.path.join(self.build_dir, 'vmlinux')
        with open(file_path, 'wb') as f:
            cmd = ['docker', 'run', '--rm', self.image_name, 'cat', '/os/work/kernel/vmlinux']
            subprocess.run(cmd, stdout=f, stderr=sys.stderr, check=True)

    def export_rootfs(self, blockdev):
        # TODO: docker run --rm r4s-qemu:latest tar -cj -C /os/work/kernel ./ > kernel-src.tar.bz2
        cmd = ['docker', 'run', '--rm', self.image_name, 'tar', 'cj', "--xattrs-include='*.*'", '--numeric-owner',
               '-C', '/os/rootfs', './']
        rootfs_tarball_path = os.path.join(self.build_dir, 'rootfs.tar.bz2')
        with open(rootfs_tarball_path, 'wb') as f:
            subprocess.run(cmd, stdout=f, check=True, stderr=sys.stderr)
        mnt_workdir_root = os.path.join(self.build_dir, 'mnt')
        mnt_workdir_boot = os.path.join(self.build_dir, 'mnt-boot')
        if not os.path.exists(mnt_workdir_root):
            os.makedirs(mnt_workdir_root)
        if not os.path.exists(mnt_workdir_boot):
            os.makedirs(mnt_workdir_boot)
        rootfs_dev = '%sp2' % blockdev
        bootfs_dev = '%sp1' % blockdev
        with builder.loopmount.mount_simple(rootfs_dev, mnt_workdir_root):
            pwd = os.getcwd()
            os.chdir(mnt_workdir_root)
            cmd = ['tar', 'xpf', rootfs_tarball_path, "--xattrs-include='*.*'", '--numeric-owner',
                   '-C', mnt_workdir_root]
            subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)
            os.chdir(pwd)
            fstab_path = os.path.join(mnt_workdir_root, 'etc', 'fstab')
            with open(fstab_path, 'w') as fstab_f:
                self.write_fstab(fstab_f, blockdev)
            with builder.loopmount.mount_simple(bootfs_dev, mnt_workdir_boot):
                srcdir = os.path.join(mnt_workdir_root, 'boot', '.')
                targetdir = os.path.join(mnt_workdir_boot)
                cmd = ['rsync', '-av', srcdir, targetdir]
                subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)

    def build(self):
        print('generating dockerfile...')
        dockerfile_path = self.generate_dockerfile()
        print('dockerfile generated: %s' % dockerfile_path)
        print('building image %s...' % self.image_name)
        self.build_docker_image(dockerfile_path)
        print('image done, allocating space for rootfs...')
        image_path = self.allocate_image()
        print('image allocated: %s' % image_path)
        with builder.loopmount.mount_loopdev(image_path) as blockdev:
            print('partitioning image %s' % blockdev)
            self.partition_device(blockdev)
            self.upload_firmware_to_device(blockdev)
            self.export_vmlinux()
