from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    install_requires = f.read().split("\n")

setup(
    name="com_link_rt",
    version="0.7.5",
    author="Emeteil",
    author_email="vorobievdima43@gmail.com",
    description="Real-time communication library for robotics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Emeteil/com_link_rt",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=install_requires
)
