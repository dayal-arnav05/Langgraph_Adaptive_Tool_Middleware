"""
Setup configuration for langgraph-tool-middleware
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="langgraph-tool-middleware",
    version="0.1.0",
    author="Arnav Dayal",
    author_email="dayalarnav05@gmail.com",
    description="Production-ready tool execution middleware for LangGraph with retry, circuit breakers, and error recovery",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dayal-arnav05/Langgraph_Adaptive_Tool_Middleware.git",
    packages=find_packages(include=["src", "src.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "langgraph>=0.0.1",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "langgraph-test=test.compare:main",
        ],
    },
)

