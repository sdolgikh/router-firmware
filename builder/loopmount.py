from contextlib import contextmanager
import subprocess
import sys


def get_free_loopdev():
    with subprocess.Popen(['losetup', '-f'], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        output, err = p.communicate()
        if p.returncode != 0:
            print(err.decode('utf-8'))
            raise RuntimeError('get_free_loopdev failed')
        return output.decode('utf-8').strip()


def mount_losetup(dev, image_path):
    subprocess.run(['losetup', '-P', dev, image_path], check=True, stdout=sys.stdout, stderr=sys.stderr)


def release_loopdev(dev):
    subprocess.run(['losetup', '-d', dev], check=True, stdout=sys.stdout, stderr=sys.stderr)


def rescan_partitions(dev):
    subprocess.run(['losetup', '-P', dev], check=True, stdout=sys.stdout, stderr=sys.stderr)


@contextmanager
def mount_loopdev(image_path):
    d = get_free_loopdev()
    mount_losetup(d, image_path)
    try:
        yield d
    finally:
        release_loopdev(d)
