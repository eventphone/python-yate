from setuptools import setup

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name='python-yate',
    version='0.1',
    packages=['yate'],
    url='www.eventphone.de',
    license='MIT',
    author='Martin Lang',
    long_description=long_description,
    long_description_content_type="text/markdown",
    author_email='Martin.Lang@rwth-aachen.de',
    description='An (asyncio enabled) python library for yate IVRs and extmodules',
    install_requires=[
        'async_timeout',
    ],
)
