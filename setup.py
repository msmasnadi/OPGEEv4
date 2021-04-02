from opgee.version import VERSION

# Build the full version with MCS on when running on ReadTheDocs.
# In normal mode, MCS is an optional install.
# import os
# import platform
#
# if platform.system() != 'Windows':
#     # Unfortunately, this stalled on Windows when I tested it...
#     import ez_setup
#     ez_setup.use_setuptools(version='36.7.2')


from setuptools import setup

requirements = [
    'ipython>=6.5',
    # 'tornado>=5.1', # may not be needed
    'future>=0.16.0',
    'lxml>=4.2.5',
    'numpy>=1.15.2',
    'pandas>=0.23.3',
    # 'seaborn>=0.9.0',
    'semver>=2.8.1',
    'sphinx-argparse>=0.2.1',
    # 'scipy>=1.1.0',
]

long_description = '''
opgee
=======

The ``opgee`` package provides ...

Full documentation and a tutorial are available at
https://opgee.readthedocs.io.

Core functionality
------------------

* TBD

Who do I talk to?
------------------

* TBD
'''

setup(
    name='opgee',
    version=VERSION,
    description='Python 3 package implementing life cycle analysis of oil fields',
    platforms=['Windows', 'MacOS', 'Linux'],

    packages=['opgee'],
    entry_points={'console_scripts': ['opg = opgee.tool:main']},
    install_requires=requirements,
    include_package_data = True,

    # extras_require=extras_requirements,

    url='https://github.com/rjplevin/opgee',
    download_url='https://github.com/rjplevin/opgee/opgee.git',
    license='MIT License',
    author='Richard Plevin',
    author_email='rich@plevin.com',

    classifiers=[
          # 'Development Status :: 5 - Production/Stable',
          'Development Status :: 2 - Pre-Alpha',
          'License :: OSI Approved :: MIT License',
          'Intended Audience :: Science/Research',
          ],

    zip_safe=True,
)
