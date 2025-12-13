from setuptools import setup
import os

this_dir = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(this_dir, "README.md"), "r") as f:
    long_description = f.read()

setup(
    name='python-yate',
    version='0.5.0',
    packages=['yate'],
    url='https://github.com/eventphone/python-yate',
    license='MIT',
    author='Martin Lang',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author_email='Martin.Lang@rwth-aachen.de',
    description='An (asyncio enabled) python library for yate IVRs and extmodules',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
    ],
    entry_points={
        "console_scripts": [
            "yate_callgen=yate.callgen:main",
        ],
    },
)
