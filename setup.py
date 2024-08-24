from setuptools import setup, find_packages

with open("README.md", 'r') as f:
    readme_text: str = f.read()

setup(
    name="newguy103-chatinterface-client",
    version='0.1.0',
    description="Client for chatinterface-server.",
    long_description=readme_text,
    long_description_content_type="text/markdown",
    author="NewGuy103",
    author_email="userchouenthusiast@gmail.com",
    install_requires=[
        "platformdirs",
        "pyside6",
        "websockets",
        "msgpack",
        "qasync",
        "httpx",
        "keyring"
    ],
    license="GPL v3.0",
    packages=find_packages()
)
