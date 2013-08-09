"""setup.py - build python-javabridge

python-javabridge is licensed under the BSD license.  See the
accompanying file LICENSE for details.

Copyright (c) 2003-2009 Massachusetts Institute of Technology
Copyright (c) 2009-2013 Broad Institute
All rights reserved.

"""

import errno
import glob
import logging
import os
import sys
import subprocess
import traceback
from setuptools import setup, Extension
from numpy import get_include
from distutils.command.build import build as _build

from javabridge.locate import *

logger = logging.getLogger(__name__)

def ext_modules():
    extensions = []
    extra_link_args = None
    if is_win:
        extra_link_args = ['/MANIFEST']
        extensions += [Extension(name="_get_proper_case_filename",
                                 sources=["get_proper_case_filename.c"],
                                 libraries=["shlwapi", "shell32", "ole32"],
                                 extra_link_args=extra_link_args)]
    try:
        java_home = find_javahome()
        jdk_home = find_jdk()
        logger.debug("Using jdk_home = %s" % jdk_home)
        include_dirs = [get_include()]
        libraries = None
        library_dirs = None
        javabridge_sources = [ "_javabridge.pyx" ]
        if is_win:
            if jdk_home is not None:
                jdk_include = os.path.join(jdk_home, "include")
                jdk_include_plat = os.path.join(jdk_include, sys.platform)
                include_dirs += [jdk_include, jdk_include_plat]
            if is_mingw:
                #
                # Build libjvm from jvm.dll on Windows.
                # This assumes that we're using mingw32 for build
                #
                cmd = ["dlltool", "--dllname", 
                       os.path.join(jdk_home,"jre\\bin\\client\\jvm.dll"),
                       "--output-lib","libjvm.a",
                       "--input-def","jvm.def",
                       "--kill-at"]
                p = subprocess.Popen(cmd)
                p.communicate()
                library_dirs = [os.path.abspath(".")]
            else:
                #
                # Use the MSVC lib in the JDK
                #
                jdk_lib = os.path.join(jdk_home, "lib")
                library_dirs = [jdk_lib]
                javabridge_sources.append("strtoull.c")

            libraries = ["jvm"]
        elif sys.platform == 'darwin':
            javabridge_sources += [ "mac_javabridge_utils.c" ]
            include_dirs += ['/System/Library/Frameworks/JavaVM.framework/Headers']
            extra_link_args = ['-framework', 'JavaVM']
        elif sys.platform.startswith('linux'):
            include_dirs += [os.path.join(java_home,'include'),
                             os.path.join(java_home,'include','linux')]
            library_dirs = [os.path.join(java_home,'jre','lib','amd64','server')]
            libraries = ["jvm"]
        extensions += [Extension(name="javabridge._javabridge",
                                 sources=javabridge_sources,
                                 libraries=libraries,
                                 library_dirs=library_dirs,
                                 include_dirs=include_dirs,
                                 extra_link_args=extra_link_args)]
    except Exception, e:
        print "WARNING: Java and JVM is not installed - Images will be loaded using PIL (%s)"%(str(e))

    return extensions

def needs_compilation(target, *sources):
    try:
        target_date = os.path.getmtime(target)
    except OSError, e:
        if e.errno != errno.ENOENT:
            raise
        return True
    for source in sources:
        source_date = os.path.getmtime(source)
        if source_date > target_date:
            return True
    return False

def build_jar_from_single_source(jar, source):
    if needs_compilation(jar, source):
        javac_command = ['javac', source]
        print ' '.join(javac_command)
        subprocess.check_call(javac_command)
        jar_command = ['jar', 'cf', jar]
        for klass in glob.glob(source[:source.rindex('.')] + '*.class'):
            jar_command.extend(['-C', 'java', klass[klass.index('/') + 1:]])
        print ' '.join(jar_command)
        subprocess.check_call(jar_command)

def build_runnablequeue():
    jar = 'javabridge/jars/runnablequeue.jar'
    source = 'java/org/cellprofiler/runnablequeue/RunnableQueue.java'
    build_jar_from_single_source(jar, source)

def build_findlibjvm():
    jar = 'javabridge/jars/findlibjvm.jar'
    source = 'java/org/cellprofiler/findlibjvm.java'
    build_jar_from_single_source(jar, source)

def build_java():
    print "running build_java"
    build_runnablequeue()
    build_findlibjvm()

class build(_build):
    def run(self, *args, **kwargs):
        build_java()
        return _build.run(self, *args, **kwargs)


if __name__ == '__main__':
    if '/' in __file__:
        os.chdir(os.path.dirname(__file__))

    setup(name="python-javabridge",
          description="Python wrapper for the Java Native Interface",
          maintainer="Vebjorn Ljosa",
          maintainer_email="ljosa@broad.mit.edu",
          packages=['javabridge'],
          package_data={"javabridge": ['jars/*.jar']},
          ext_modules=ext_modules(),
          tests_require="nose",
          entry_points={'nose.plugins.0.10': [
                'javabridge = javabridge.noseplugin:JavabridgePlugin'
                ]},
          test_suite="nose.collector",
          cmdclass={'build': build})
    
