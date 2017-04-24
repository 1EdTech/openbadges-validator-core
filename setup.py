import os
from setuptools import setup

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
    packages=['badgecheck'],
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
        'pydux==0.2.1',
        'PyLD==0.7.1',
        'pytz==2017.2',
        'requests >= 2.13',
        'rfc3986==0.4.1',
        'validators==0.11.2',
        # 'openbadges_bakery >= 0.1.4'  # Removing until openbadges_bakery does not require Django.
    ]
)
