from builder.multistep import BuilderMultistep
import sys
import os


if __name__ == '__main__':
    target = 'baremetal'
    if len(sys.argv) > 1 and sys.argv[1] == 'qemu':
        target = 'qemu'
    print('target: ', target)
    build_dir = os.path.join(os.path.dirname(__file__), 'build', target)
    builder = BuilderMultistep(build_dir, target)
    builder.build()
