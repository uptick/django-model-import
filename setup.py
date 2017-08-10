import os
import sys

from setuptools import find_packages, setup

version = '0.0.1'

setup(
    name='djangomodelimport',
    version=version,
    author='Aidan Lister',
    author_email='aidan@aidanlister.com',
    maintainer='Aidan Lister',
    maintainer_email='aidan@aidanlister.com',
    url='https://github.com/ABASystems/python-fuku',
    description='Fast CSV imports using django model forms.',
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['*.txt', '*.js', '*.html', '*.*']},
    install_requires=[
        'setuptools', 'python-dateutil', 'tablib'
    ],
    zip_safe=False,
)
