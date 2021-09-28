from distutils.core import setup, Extension

module1 = Extension("mytrace", sources=["mytrace.c"])

setup(
    name="mytrace",
    version="1.0",
    description="Testing traceing from C",
    ext_modules=[module1],
)
