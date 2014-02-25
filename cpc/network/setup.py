from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

setup(
    cmdclass = {'build_ext': build_ext},
    ext_modules = [Extension("server", ["server.pyx"]),
                   Extension("server_request", ["server_request.pyx"]),
                   Extension("server_response", ["server_response.pyx"]),
                   Extension("copernicus_server", ["copernicus_server.pyx"]),
                   Extension("node", ["node.pyx"]),
                   Extension("request_handler", ["request_handler.pyx"])]
)

