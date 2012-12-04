import addonpr
try:
    from setuptools import setup
    kw = {
        'install_requires': 'docopt == 0.5.0',
    }
except ImportError:
    from distutils.core import setup
    kw = {}


setup(
    name='addon-pr',
    version=addonpr.__version__,
    author='Team XBMC',
    license='GPLv2',
    description='addon-pr helps to process XBMC addons pull requests',
    long_description=open('README.rst').read(),
    url='http://xbmc.org',
    packages=['addonpr'],
    scripts=['bin/addon-pr'],
    classifiers=['Development Status :: 4 - Beta',
                 'Topic :: Software Development',
                 'License :: OSI Approved :: GNU General Public License (GPL)',
                 'Intended Audience :: Developers',
                 'Programming Language :: Python'],
    **kw
)
