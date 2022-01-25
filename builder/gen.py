from jinja2 import Environment, PackageLoader
import multiprocessing


class DockerfileGen:

    def __init__(self, target):
        self.jinja_env = Environment(
            loader=PackageLoader('builder')
        )
        self.template = self.jinja_env.get_template('Dockerfile.template')
        self.target = target

    def get_context(self):
        ctx = {'IS_QEMU': self.target == 'qemu',
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
