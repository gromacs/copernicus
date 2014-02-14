from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

setup(
    cmdclass = {'build_ext': build_ext},
    ext_modules = [Extension("value", ["value.pyx"]),
                   Extension("active_conn", ["active_conn.pyx"]),
                   Extension("active_inst", ["active_inst.pyx"]),
                   Extension("active_network", ["active_network.pyx"]),
                   Extension("active_value", ["active_value.pyx"]),
                   Extension("project", ["project.pyx"]),
                   Extension("vtype", ["vtype.pyx"]),
                   Extension("readxml", ["readxml.pyx"])]
)

