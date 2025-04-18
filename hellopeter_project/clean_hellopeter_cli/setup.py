#!/usr/bin/env python3
"""
Setup script for the HelloPeter CLI package.
"""
import os
from setuptools import setup, find_packages

# Get the long description from the README file
with open(os.path.join(os.path.dirname(__file__), "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Get version from the package
with open(os.path.join("hellopeter_cli", "__init__.py"), encoding="utf-8") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"\'')
            break

setup(
    name="hellopeter-cli",
    version=version,
    description="A command-line tool for extracting reviews and statistics from HelloPeter",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="HelloPeter CLI Team",
    author_email="example@example.com",
    url="https://github.com/yourusername/hellopeter-cli",
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "hellopeter-cli=hellopeter_cli.cli:main",
        ],
    },
    install_requires=[
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "SQLAlchemy>=2.0.23",
        "pandas>=2.1.1",
        "tqdm>=4.66.1",
        "backoff>=2.2.1",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    keywords="hellopeter, reviews, statistics, api, cli",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/hellopeter-cli/issues",
        "Source": "https://github.com/yourusername/hellopeter-cli",
    },
) 