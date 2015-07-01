from setuptools import setup

install_requires = (
    "requests",
    "requests[security]"
    )

setup(name='content-copy-tool',
      version='0.4',
      py_modules=['lib'],
      install_requires=install_requires,
      )
