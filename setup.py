from setuptools import setup, find_packages

setup(
    name="itch_main",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4",
        "aiohttp",
        "requests"
    ],
    entry_points={
        "console_scripts": [
            "itch-scraper=itch_main.main:main"
        ]
    },
)
