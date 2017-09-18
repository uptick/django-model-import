import os
import re

from setuptools import setup

# Get version this way, so that we don't load any modules.
with open('./djangomodelimport/__init__.py') as f:
    exec(re.search(r'VERSION = .*', f.read(), re.DOTALL).group())

try:
    setup(
        name='django-model-import',
        packages=['djangomodelimport'],
        version=__version__,
        description="Fast CSV imports using django model forms.",
        long_description=open(os.path.join(os.path.dirname(__file__), 'README.md')).read(),
        license='BSD',
        author='Uptick',
        author_email='dev@uptickhq.com',
        url='https://github.com/ABASystems/django-model-import',
        keywords=['csv', 'import'],
        classifiers=[
            'Development Status :: 3 - Alpha',
            'Environment :: Web Environment',
            'Intended Audience :: Developers',
            'Natural Language :: English',
            'License :: OSI Approved :: BSD License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3.6',
        ],
        install_requires=[
            'python-dateutil>=2.6.0',
            'tablib>=0.11.5',
        ],
    )
except NameError:
    raise RuntimeError("Unable to determine version.")
