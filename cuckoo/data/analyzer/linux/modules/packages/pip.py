#
#
#

import os
import contextlib
import lzma
import tarfile


from lib.common.abstracts import Package

class Pip(Package):
    """Generic analysis package. Uses shell based execution."""

    def __init__(self, *args, **kwargs):
        Package.__init__(self, *args, **kwargs)

    def start(self, path):
        # os.chmod(path, 0o755)
        # extract the package
        with contextlib.closing(lzma.LZMAFile(path)) as xz:
            with tarfile.open(fileobj=xz) as f:
                f.extractall('.')
        # install the package
        python = "/usr/bin/python"
        args = "setup.py install"
        return self.execute(python, args=args)
