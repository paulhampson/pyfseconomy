import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='pyfseconomy',
    version='0.2.0',
    author="Paul Hampson",
    description='Library for interacting with the FS Economy API',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/paulhampson/pyfseconomy',
    packages=setuptools.find_packages(),
    package_data={
        "pyfseconomy": ["icaodata.csv"],
    },
    install_requires=[
        'pandas~=1.1.3',
        'requests~=2.24.0',
        'geographiclib~=1.50',
    ],
    python_requires='>=3.8',
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Natural Language :: English",
        "Topic :: Games/Entertainment"
    ],
)
