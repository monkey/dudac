import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="dudac",
    version="0.17.dev",
    author="Eduardo Silva",
    author_email="edsiper@gmail.com",
    description=("DudaC is a command line interface for the web services"
                 "framework 'Duda'"),
    license="GPLv2+",
    keywords="HTTP monkey duda",
    url="http://duda.io",
    packages=find_packages(),
    long_description=read('README'),
    include_package_data=True,
    classifiers = [
        #'Development Status :: 1 - Planning',
        #'Development Status :: 2 - Pre-Alpha',
        #'Development Status :: 3 - Alpha',
        'Development Status :: 4 - Beta',
        #'Development Status :: 5 - Production/Stable',
        #'Development Status :: 6 - Mature',
        #'Development Status :: 7 - Inactive',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)'
        'Programming Language :: Python',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': [
            'dudac = dudaclient.main:main'
        ]
    },
)
