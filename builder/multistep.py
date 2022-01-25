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
        for fname in ['idbloader.img', 'u-boot.itb']:
            out_path = os.path.join(self.build_dir, fname)
            with open(out_path, 'wb') as f:
                cmd = ['docker', 'run', '--rm', self.image_name, 'cat', '/os/%s' % fname]
                subprocess.run(cmd, stdout=f, check=True, stderr=sys.stderr)
            seek = 64 if fname == 'idbloader.img' else 16384
            cmd = ['dd', 'if=%s' % out_path, 'of=%s' % blockdev, 'seek=%s' % seek, 'conv=notrunc']
            print(' '.join(cmd))
            subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr)

    def export_rootfs(self, blockdev):
        cmd = ['docker', 'run', '--rm', 'r4s:latest', 'tar', 'cj', "--xattrs-include='*.*'", '--numeric-owner',
               '-C', '/os/rootfs', './']
        rootfs_tarball_path = os.path.join(self.build_dir, 'rootfs.tar.bz2')
        with open(rootfs_tarball_path, 'wb') as f:
            subprocess.run(cmd, stdout=f, check=True, stderr=sys.stderr)
        mnt_workdir = os.path.join(self.build_dir, 'mnt')
        if not os.path.exists(mnt_workdir):
            os.makedirs(mnt_workdir)
        rootfs_dev = '%sp2' % blockdev
        with builder.loopmount.mount_simple(rootfs_dev, mnt_workdir):
            pwd = os.getcwd()
            os.chdir(mnt_workdir)
            cmd = ['tar', 'xpf', rootfs_tarball_path, "--xattrs-include='*.*'", '--numeric-owner',
                   '-C', mnt_workdir]
            print(' '.join(cmd))
            subprocess.run(cmd, check=True, stderr=sys.stderr, stdout=sys.stdout)
            os.chdir(pwd)
            # TODO: create_fstab

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
            input('press any key')


