from setuptools import setup, find_packages

setup(
    name="ot2-lcm",
    version="0.1.0",
    packages=find_packages(where="app"),
    package_dir={"": "app"},
    install_requires=[
        "gradio>=3.50.0",
        "paho-mqtt>=1.6.1",
        "pandas>=2.0.0",
        "pymongo>=4.5.0",
        "prefect>=2.13.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "plotly>=5.18.0",
        "asyncpg>=0.29.0",
        "prometheus-client>=0.19.0",
        "motor>=3.3.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.1",
            "pytest-env>=1.0.1",
            "aioresponses>=0.7.4",
            "asynctest>=0.13.0",
            "coverage>=7.3.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.5.1",
            "pylint>=2.17.5",
            "pre-commit>=3.3.3",
            "docker>=6.1.3",
        ]
    },
    python_requires=">=3.9",
) 