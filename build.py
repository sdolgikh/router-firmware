from jinja2 import Environment, PackageLoader

import sys
import os
import multiprocessing


class DockerfileGen():

    def __init__(self):
        self.jinja_env = Environment(
            loader=PackageLoader('gen')
        )
        self.template = self.jinja_env.get_template('Dockerfile.template')
        self.is_qemu = False

    def get_context(self):
        ctx = {'IS_QEMU': self.is_qemu,
               'CONCURRENCY_THREADS': multiprocessing.cpu_count(),
               'GENTOO_MIRROR': self.get_gentoo_mirror()}
        return ctx

    def generate(self, outfile):
        ctx = self.get_context()
        txt = self.template.render(**ctx)
        outfile.write(txt)
        outfile.write('\n')

    def get_build_numthreads(self):
        return multiprocessing.cpu_count()

    def get_gentoo_mirror(self):
        return "https://mirror.yandex.ru/gentoo-distfiles"

    
class QemuDockerfileGen(DockerfileGen):

    def __init__(self):
        super().__init__()
        self.is_qemu = True


class BareMetalGen(DockerfileGen):
    pass


if __name__ == '__main__':
    target = 'baremetal'
    if len(sys.argv) > 1 and sys.argv[1] == 'qemu':
        gen = QemuDockerfileGen()
        target = 'qemu'
    else:
        gen = BareMetalGen()
    print('target: ', target)
    build_dir = os.path.join(os.path.dirname(__file__), 'build', target)
    if not os.path.exists(build_dir):
        os.makedirs(build_dir)
    outfile_path = os.path.join(build_dir, 'Dockerfile')
    with open(outfile_path, 'w') as f:
        gen.generate(f)
    print('file generated: %s' % outfile_path)
