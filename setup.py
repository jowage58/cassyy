import re
import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open(os.path.join(here, 'cassyy', "__init__.py")) as fp:
    version = re.compile(
        r""".*__version__ = ["'](.*?)['"]""", re.S
    ).match(fp.read()).group(1)

setup(
    name='cassyy',
    version=version,
    description='Simple Apereo Central Authentication Service (CAS) client',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/jowage58/cassyy/',
    author='John Wagenleitner',
    author_email='johnwa@mail.fresnostate.edu',
    keywords='Authentication SSO CAS',
    packages=['cassyy'],
    python_requires='>=3.8, <4',
    project_urls={
        'Bug Reports': 'https://github.com/jowage58/cassyy/issues',
        'Source': 'https://github.com/jowage58/cassyy/',
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Database',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
)
