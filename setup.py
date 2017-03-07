import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# import VERSION
execfile(os.path.join(os.path.dirname(__file__), 'badgecheck/version.py'))

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))



setup(
    name='badgecheck',
    version=".".join(map(str, VERSION)),
    packages=['badgecheck'],
    include_package_data=True,
    license='Apache 2',
    description='A simple Django app to conduct Web-based polls.',
    long_description=README,
    url='http://badgecheck.org/',
    author='Nate Otto',
    author_email='notto@concentricsky.com',
    classifiers=[
        'Environment :: Console',
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Education',
        'Topic :: Utilities',
        'Intended Audience :: Developers'
    ],
    install_requires=[
        'django >= 1.7',
        'requests >= 2.5',
        'djangorestframework >= 3.1',
        'openbadges_bakery >= 0.1.4'
    ]
)
