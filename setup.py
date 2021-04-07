#! /usr/bin/env python
# ===============================================================================
# Copyright 2014-2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ===============================================================================

# System imports
import os
import sys
import sysconfig
import time
from setuptools import setup, Extension
import setuptools.command.install as orig_install
import setuptools.command.develop as orig_develop
import distutils.command.build as orig_build
from os.path import join as jp
from distutils.sysconfig import get_config_vars
from Cython.Build import cythonize
import glob
import numpy as np
import scripts.build_backend as build_backend

try:
    from ctypes.utils import find_library
except ImportError:
    from ctypes.util import find_library

IS_WIN = False
IS_MAC = False
IS_LIN = False

dal_root = os.environ.get('DALROOT')

if 'linux' in sys.platform:
    IS_LIN = True
    lib_dir = jp(dal_root, 'lib', 'intel64')
elif sys.platform == 'darwin':
    IS_MAC = True
    lib_dir = jp(dal_root, 'lib')
elif sys.platform in ['win32', 'cygwin']:
    IS_WIN = True
    lib_dir = jp(dal_root, 'lib', 'intel64')
else:
    assert False, sys.platform + ' not supported'


def get_lib_suffix():

    def walk_ld_library_path():
        if IS_WIN:
            ld_library_path = os.environ.get('LIBRARY_LIB')
            if ld_library_path is None:
                ld_library_path = f"{os.environ.get('CONDA_PREFIX')}/Library/lib"
        else:
            ld_library_path = os.environ.get('LD_LIBRARY_PATH', None)

        if ld_library_path is None:
            return None

        libs = []
        if IS_WIN:
            ld_library_path = ld_library_path.split(';')
        else:
            ld_library_path = ld_library_path.split(':')
        while '' in ld_library_path:
            ld_library_path.remove('')
        for lib_path in ld_library_path:
            for _, _, new_files in os.walk(lib_path):
                libs += new_files

        for lib in libs:
            if 'onedal_core' in lib:
                return 'onedal'
            if 'daal_core' in lib:
                return 'daal'
        return None

    def walk_libdir():
        global lib_dir

        for _, _, libs in os.walk(lib_dir):
            for lib in libs:
                if 'onedal_core' in lib:
                    return 'onedal'
                if 'daal_core' in lib:
                    return 'daal'
        return None

    ld_lib_path_suffix = walk_ld_library_path()
    lib_dir_suffix = walk_libdir()
    if find_library('onedal_core') is not None or \
       ld_lib_path_suffix == 'onedal' or \
            lib_dir_suffix == 'onedal':
        return 'onedal'
    if find_library('daal_core') is not None or \
       ld_lib_path_suffix == 'daal' or \
            lib_dir_suffix == 'daal':
        return 'daal'

    raise ImportError('Unable to import oneDAL or oneDAL lib')


def get_win_major_version():
    lib_name = find_library('onedal_core')
    if lib_name is None:
        return ''
    version = lib_name.split('\\')[-1].split('.')[1]
    try:
        version = '.' + str(int(version))
    except ValueError:
        version = ''
    return version


d4p_version = (os.environ['DAAL4PY_VERSION'] if 'DAAL4PY_VERSION' in os.environ
               else time.strftime('2021.%Y%m%d.%H%M%S'))

trues = ['true', 'True', 'TRUE', '1', 't', 'T', 'y', 'Y', 'Yes', 'yes', 'YES']
no_dist = True if 'NO_DIST' in os.environ and os.environ['NO_DIST'] in trues else False
no_stream = 'NO_STREAM' in os.environ and os.environ['NO_STREAM'] in trues
mpi_root = None if no_dist else os.environ['MPIROOT']
dpcpp = True if 'DPCPPROOT' in os.environ else False
dpcpp_root = None if not dpcpp else os.environ['DPCPPROOT']
dpctl = True if dpcpp and 'DPCTLROOT' in os.environ else False
dpctl_root = None if not dpctl else os.environ['DPCTLROOT']


daal_lib_dir = lib_dir if (IS_MAC or os.path.isdir(
    lib_dir)) else os.path.dirname(lib_dir)
ONEDAL_LIBDIRS = [daal_lib_dir]
if IS_WIN:
    ONEDAL_LIBDIRS.append(f"{os.environ.get('CONDA_PREFIX')}/Library/lib")

if no_stream:
    print('\nDisabling support for streaming mode\n')
if no_dist:
    print('\nDisabling support for distributed mode\n')
    DIST_CFLAGS = []
    DIST_CPPS = []
    MPI_INCDIRS = []
    MPI_LIBDIRS = []
    MPI_LIBS = []
    MPI_CPPS = []
else:
    DIST_CFLAGS = ['-D_DIST_', ]
    DIST_CPPS = ['src/transceiver.cpp']
    MPI_INCDIRS = [jp(mpi_root, 'include')]
    MPI_LIBDIRS = [jp(mpi_root, 'lib')]
    MPI_LIBNAME = getattr(os.environ, 'MPI_LIBNAME', None)
    if MPI_LIBNAME:
        MPI_LIBS = [MPI_LIBNAME]
    elif IS_WIN:
        if os.path.isfile(jp(mpi_root, 'lib', 'mpi.lib')):
            MPI_LIBS = ['mpi']
        if os.path.isfile(jp(mpi_root, 'lib', 'impi.lib')):
            MPI_LIBS = ['impi']
        assert MPI_LIBS, "Couldn't find MPI library"
    else:
        MPI_LIBS = ['mpi']
    MPI_CPPS = ['src/mpi/mpi_transceiver.cpp']

if dpcpp:
    DPCPP_CFLAGS = ['-D_DPCPP_ -fno-builtin-memset' '-fsycl']
    DPCPP_LIBS = ['OpenCL', 'sycl', 'onedal_sycl']
    if IS_LIN:
        DPCPP_LIBDIRS = [jp(dpcpp_root, 'linux', 'lib')]
    elif IS_WIN:
        DPCPP_LIBDIRS = [jp(dpcpp_root, 'windows', 'lib')]

else:
    DPCPP_CFLAGS = []
    DPCPP_LIBS = []
    DPCPP_LIBDIRS = []


def get_sdl_cflags():
    if IS_LIN or IS_MAC:
        return DIST_CFLAGS + ['-fstack-protector-strong', '-fPIC',
                              '-D_FORTIFY_SOURCE=2', '-Wformat',
                              '-Wformat-security', '-fno-strict-overflow',
                              '-fno-delete-null-pointer-checks']
    elif IS_WIN:
        return DIST_CFLAGS + ['-GS', ]


def get_sdl_ldflags():
    if IS_LIN:
        return ['-Wl,-z,noexecstack,-z,relro,-z,now,-fstack-protector-strong,'
                '-fno-strict-overflow,-fno-delete-null-pointer-checks,-fwrapv']
    elif IS_MAC:
        return ['-fstack-protector-strong',
                '-fno-strict-overflow',
                '-fno-delete-null-pointer-checks',
                '-fwrapv']
    elif IS_WIN:
        return ['-NXCompat', '-DynamicBase']


def get_daal_type_defines():
    daal_type_defines = ['DAAL_ALGORITHM_FP_TYPE',
                         'DAAL_SUMMARY_STATISTICS_TYPE',
                         'DAAL_DATA_TYPE']
    return [(d, 'double') for d in daal_type_defines]


def get_build_options():
    include_dir_plat = [os.path.abspath(
        './src'), os.path.abspath('./onedal'), dal_root + '/include', ]
    # FIXME it is a wrong place for this dependency
    if not no_dist:
        include_dir_plat.append(mpi_root + '/include')
    using_intel = os.environ.get('cc', '') in ['icc', 'icpc', 'icl', 'dpcpp']
    eca = ['-DPY_ARRAY_UNIQUE_SYMBOL=daal4py_array_API',
           '-DD4P_VERSION="' + d4p_version + '"', '-DNPY_ALLOW_THREADS=1']
    ela = []

    if using_intel and IS_WIN:
        include_dir_plat.append(
            jp(os.environ.get('ICPP_COMPILER16', ''), 'compiler', 'include'))
        eca += ['-std=c++17', '-w', '/MD']
    elif not using_intel and IS_WIN:
        eca += ['-wd4267', '-wd4244', '-wd4101', '-wd4996', '/MD']
    else:
        eca += ['-std=c++17', '-w', ]  # '-D_GLIBCXX_USE_CXX11_ABI=0']

    # Security flags
    eca += get_sdl_cflags()
    ela += get_sdl_ldflags()

    lib_suffix = get_lib_suffix()

    if IS_WIN:
        major_version = get_win_major_version()
        libraries_plat = [f'{lib_suffix}_core_dll{major_version}']
    else:
        libraries_plat = [f'{lib_suffix}_core', f'{lib_suffix}_thread']

    if IS_MAC:
        ela.append('-stdlib=libc++')
        ela.append("-Wl,-rpath,{}".format(daal_lib_dir))
        ela.append("-Wl,-rpath,@loader_path/../..")
    elif IS_WIN:
        ela.append('-IGNORE:4197')
    elif IS_LIN and not any(x in os.environ and '-g' in os.environ[x]
                            for x in ['CPPFLAGS', 'CFLAGS', 'LDFLAGS']):
        ela.append('-s')
    if IS_LIN:
        ela.append("-fPIC")
        ela.append("-Wl,-rpath,$ORIGIN/../..")
    return eca, ela, include_dir_plat, libraries_plat


def getpyexts():
    eca, ela, include_dir_plat, libraries_plat = get_build_options()

    onedal_libraries = libraries_plat.copy()
    onedal_libraries.extend(['onedal'])

    import distutils.dir_util
    from distutils.file_util import copy_file

    # TODO
    import re
    filter_rule = re.compile(r'.*')
    cpp_files = glob.glob("onedal/**/**/*.cpp")
    pyx_files = glob.glob("onedal/**/*.pyx")
    pxi_files = glob.glob("onedal/**/*.pxi")

    cpp_files = [s for s in cpp_files if filter_rule.match(s)]
    pyx_files = [s for s in pyx_files if filter_rule.match(s)]
    pxi_files = [s for s in pxi_files if filter_rule.match(s)]

    distutils.dir_util.create_tree('build', pyx_files)
    print('cpp_files:', cpp_files)
    print('pyx_files:', pyx_files)
    for f in pyx_files:
        copy_file(f, jp('build', f))

    main_pyx = 'onedal/onedal.pyx'
    main_host_pyx = 'build/onedal/onedal_host.pyx'
    main_dpc_pyx = 'build/onedal/onedal_dpc.pyx'
    copy_file(main_pyx, main_host_pyx)
    copy_file(main_pyx, main_dpc_pyx)

    for f in pxi_files:
        copy_file(f, jp('build', f))

    pyx_host_files = glob.glob("build/onedal/**/*_host.pyx")
    pyx_dpc_files = glob.glob("build/onedal/**/*_dpc.pyx")

    print(pyx_host_files)
    print(pyx_dpc_files)

    print(pyx_host_files + cpp_files)
    exts = []

    ext = Extension('_onedal4py_host',
                    sources=[main_host_pyx] + cpp_files,
                    include_dirs=include_dir_plat + [np.get_include()],
                    extra_compile_args=eca,
                    extra_link_args=ela,
                    define_macros=[
                        ('NPY_NO_DEPRECATED_API',
                         'NPY_1_7_API_VERSION'),
                    ],
                    libraries=onedal_libraries,
                    library_dirs=ONEDAL_LIBDIRS,
                    language='c++')

    exts.extend(cythonize(ext))

    # ext = Extension('_daal4py',
    #                 [os.path.abspath('src/daal4py.cpp'),
    #                  os.path.abspath('build/daal4py_cpp.cpp'),
    #                  os.path.abspath('build/daal4py_cy.pyx')]
    #                 + DIST_CPPS,
    #                 depends=glob.glob(jp(os.path.abspath('src'), '*.h')),
    #                 include_dirs=include_dir_plat + [np.get_include()],
    #                 extra_compile_args=eca,
    #                 define_macros=get_daal_type_defines(),
    #                 extra_link_args=ela,
    #                 libraries=libraries_plat,
    #                 library_dirs=ONEDAL_LIBDIRS,
    #                 language='c++')
    # exts.extend(cythonize(ext))

    if dpcpp:
        if IS_LIN or IS_MAC:
            runtime_library_dirs = ["$ORIGIN/onedal"]
        elif IS_WIN:
            runtime_library_dirs = []

        ext = Extension('_onedal4py_dpc',
                        sources=[main_dpc_pyx],
                        include_dirs=include_dir_plat,
                        extra_compile_args=eca,
                        extra_link_args=eca,
                        libraries=['dpc_backend'],
                        library_dirs=['onedal'],
                        runtime_library_dirs=runtime_library_dirs,
                        language='c++')
        exts.extend(cythonize(ext))
        # ext = Extension('_oneapi',
        #                 [os.path.abspath('src/oneapi/oneapi.pyx'), ],
        #                 depends=['src/oneapi/oneapi.h', 'src/oneapi/dpc_backend.h'],
        #                 include_dirs=include_dir_plat + [np.get_include()],
        #                 extra_compile_args=eca,
        #                 extra_link_args=ela,
        #                 libraries=['dpc_backend'],
        #                 library_dirs=['daal4py/oneapi'],
        #                 runtime_library_dirs=runtime_library_dirs,
        #                 language='c++')

        # exts.extend(cythonize(ext))

    if not no_dist:
        mpi_include_dir = include_dir_plat + [np.get_include()] + MPI_INCDIRS
        mpi_depens = glob.glob(jp(os.path.abspath('src'), '*.h'))
        mpi_extra_link = ela + ["-Wl,-rpath,{}".format(x) for x in MPI_LIBDIRS]
        exts.append(Extension('mpi_transceiver',
                              MPI_CPPS,
                              depends=mpi_depens,
                              include_dirs=mpi_include_dir,
                              extra_compile_args=eca,
                              define_macros=get_daal_type_defines(),
                              extra_link_args=mpi_extra_link,
                              libraries=libraries_plat + MPI_LIBS,
                              library_dirs=ONEDAL_LIBDIRS + MPI_LIBDIRS,
                              language='c++'))
    return exts


cfg_vars = get_config_vars()
for key, value in get_config_vars().items():
    if isinstance(value, str):
        cfg_vars[key] = value.replace(
            "-Wstrict-prototypes", "").replace('-DNDEBUG', '')


def gen_pyx(odir):
    gtr_files = glob.glob(
        jp(os.path.abspath('generator'), '*')) + ['./setup.py']
    src_files = [os.path.abspath('build/daal4py_cpp.h'),
                 os.path.abspath('build/daal4py_cpp.cpp'),
                 os.path.abspath('build/daal4py_cy.pyx')]
    if all(os.path.isfile(x) for x in src_files):
        src_files.sort(key=lambda x: os.path.getmtime(x))
        gtr_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        if os.path.getmtime(src_files[0]) > os.path.getmtime(gtr_files[0]):
            print('Generated files are all newer than generator code.'
                  'Skipping code generation')
            return

    from generator.gen_daal4py import gen_daal4py
    odir = os.path.abspath(odir)
    if not os.path.isdir(odir):
        os.mkdir(odir)
    gen_daal4py(dal_root, odir, d4p_version,
                no_dist=no_dist, no_stream=no_stream)


# gen_pyx(os.path.abspath('./build'))


def distutils_dir_name(dname):
    """Returns the name of a distutils build directory"""
    f = "{dirname}.{platform}-{version[0]}.{version[1]}"
    return f.format(dirname=dname,
                    platform=sysconfig.get_platform(),
                    version=sys.version_info)


class install(orig_install.install):
    def run(self):
        if dpcpp:
            build_backend.custom_build_cmake_clib()
        return super().run()


class develop(orig_develop.develop):
    def run(self):
        if dpcpp:
            build_backend.custom_build_cmake_clib()
        return super().run()


class build(orig_build.build):
    def run(self):
        if dpcpp:
            build_backend.custom_build_cmake_clib()
        return super().run()


project_urls = {
    'Bug Tracker': 'https://github.com/IntelPython/daal4py/issues',
    'Documentation': 'https://intelpython.github.io/daal4py/',
    'Source Code': 'https://github.com/IntelPython/daal4py'
}

with open('README.md', 'r', encoding='utf8') as f:
    long_description = f.read()

install_requires = []
with open('requirements.txt') as f:
    install_requires.extend(f.read().splitlines())
    if IS_MAC:
        for r in install_requires:
            if "dpcpp_cpp_rt" in r:
                install_requires.remove(r)
                break

setup(
    name="daal4py",
    description="A convenient Python API to Intel(R) oneAPI Data Analytics Library",
    author="Intel",
    version=d4p_version,
    url='https://github.com/IntelPython/daal4py',
    project_urls=project_urls,
    cmdclass={'install': install, 'develop': develop, 'build': build},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Other Audience',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering',
        'Topic :: System',
        'Topic :: Software Development',
    ],
    # setup_requires = ['numpy>=1.14', 'cython', 'jinja2'],
    # install_requires = ['numpy>=1.14', 'daal', 'dpcpp_cpp_rt'],
    packages=[
        'daal4py',
        'daal4py.oneapi',
        'daal4py.sklearn',
        'daal4py.sklearn.cluster',
        'daal4py.sklearn.decomposition',
        'daal4py.sklearn.ensemble',
        'daal4py.sklearn.linear_model',
        'daal4py.sklearn.manifold',
        'daal4py.sklearn.metrics',
        'daal4py.sklearn.neighbors',
        'daal4py.sklearn.monkeypatch',
        'daal4py.sklearn.svm',
        'daal4py.sklearn.utils',
        'daal4py.sklearn.model_selection',
        'onedal',
        'onedal.svm',
        'onedal.prims',
    ],
    package_data={
        'onedal': [
            'libdpc_backend.so',
            'dpc_backend.lib',
            'dpc_backend.dll'
        ]
    },
    ext_modules=getpyexts()
)
