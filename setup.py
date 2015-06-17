from distutils.core import setup

install_requires = (
    "requests",
    "requests[security]"
    )

setup(name='content-copy-tool',
      version='0.3',
      py_modules=['lib'],
      install_requires=install_requires,
      entry_points={'console_scripts': ['content-copy = content-copy', ], },
      )
