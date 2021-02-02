import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nx-sign-over-http",
    version="2.0.1",
    author="Sergei Ivanov",
    author_email="sivanov@networkoptix.com",
    description="Standalone sign-over-http service",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.lan.hdw.mx/dev/tools/-/tree/master/sign_over_http",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    install_requires=[
        'pyyaml',
        'aiohttp'
    ],
    package_data={
        'server': [
            'config/log.yaml',
            'config/openssl_handler/genkey.bat',
            'config/openssl_handler/genkey.sh',
            'config/signtool_handler/config.yaml',
            'config/signtool_handler/genkey.bat',
        ],
    },
)