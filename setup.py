from setuptools import setup, find_packages

setup(
    name="starloom",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "requests>=2.25.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "starloom=starloom.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
