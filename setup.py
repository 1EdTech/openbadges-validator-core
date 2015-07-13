import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='badgecheck',
    version='0.2.1-test6',
    packages=['badgecheck'],
    include_package_data=True,
    license='aGPL License',
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
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
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
        'responses >= 0.3',
        'djangorestframework >= 3.1.1',
        'openbadges_bakery == 0.1.1'
    ],
    dependency_links=[
        'git+ssh://git@stash.concentricsky.com/bp/openbadges_bakery.git@v0.1.1#egg=openbadges_bakery-0.1.1'
    ]
)
