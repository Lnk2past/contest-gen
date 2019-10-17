import os
from setuptools import setup, find_packages

about = {}
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'contestgen', '__version__.py'), 'r') as f:
    exec(f.read(), about)

with open('README.md', 'r') as f:
    readme = f.read()

with open('requirements.txt', 'r') as f:
    install_requires = f.read().split('\n')

setup(
    name=about['__title__'],
    version=about['__version__'],
    packages=find_packages(),
    author=about['__author__'],
    description=about['__description__'],
    long_description=readme,
    long_description_content_type='text/markdown',
    license=about['__license__'],
    url=about['__url__'],
    install_requires=install_requires,
    entry_points={
        'console_scripts': [
            'contestgen=contestgen.__main__:main'
        ]
    }
)
