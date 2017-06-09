import os
from setuptools import find_packages, setup

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme:
    README = readme.read()

# import VERSION
try:
    execfile(os.path.join(os.path.dirname(__file__), 'badgecheck/version.py'))
except NameError:
    exec(open(os.path.join(os.path.dirname(__file__), 'badgecheck/version.py')).read())

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))



setup(
    name='badgecheck',
    version=".".join(map(str, VERSION)),
    packages=find_packages(exclude=['tests', 'tests.*']),
    include_package_data=True,
    license='Apache 2',
    description='A python module that performs verification for Open Badges.',
    long_description=README,
    url='https://github.com/openbadges/badgecheck',
    author='Nate Otto',
    author_email='notto@concentricsky.com',
    classifiers=[
        'Environment :: Console',
        'Development Status :: 3 - Alpha',
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
        'aniso8601>=1.2.0',
        'jsonschema==2.6.0',
        'jws==0.1.3',
        'openbadges-bakery>=1.0.0b1',
        'pycrypto==2.6.1',
        'pydux==0.2.1',
        'PyLD==0.7.1',
        'pytz==2017.2',
        'requests >= 2.13',
        'requests_cache==0.4.13',
        'rfc3986==0.4.1',
        'validators==0.11.2',
    ],
    extras_require={
        'server':  ["Flask==0.12.1", 'gunicorn==19.7.1'],
    }
)
