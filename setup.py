import pathlib
import re
import sys

import setuptools as st
from setuptools.command.test import test as TestCommand


class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import tox

        errno = tox.cmdline(self.test_args)
        sys.exit(errno)


with open('README.rst') as reader:
    readme = reader.read()


init = (pathlib.Path('modelqueue') / '__init__.py').read_text()
match = re.search(r"^__version__ = '(.+)'$", init, re.MULTILINE)
version = match.group(1)

st.setup(
    name='modelqueue',
    version=version,
    description='Task queue based on Django models.',
    long_description=readme,
    author='Grant Jenks',
    author_email='contact@grantjenks.com',
    url='http://www.grantjenks.com/docs/modelqueue/',
    packages=['modelqueue'],
    tests_require=['tox'],
    cmdclass={'test': Tox},
    license='Apache 2.0',
    install_requires=['django', 'pytz'],
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ),
)
