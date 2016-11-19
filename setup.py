from setuptools import setup, find_packages


with open('README.rst', 'r') as f:
    README = f.read()


setup(name='aiompd',
      version='0.3.2',
      description='MPD (Music Player Daemon) client for asyncio',
      long_description=README,
      classifiers=[
          "License :: OSI Approved :: BSD License",
          "Operating System :: POSIX",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Topic :: System :: Networking",
          "Topic :: Multimedia :: Sound/Audio",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Development Status :: 5 - Production/Stable",
      ],
      author='Alexander Zelenyak',
      author_email='zzz.sochi@gmail.com',
      url='https://github.com/zzzsochi/aiompd',
      keywords=['mpd', 'asyncio'],
      packages=find_packages()
      )
