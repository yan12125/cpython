"""Tests for distutils.sysconfig."""
import os
import shutil
import subprocess
import sys
import textwrap
import unittest

from distutils import sysconfig
from distutils.ccompiler import get_default_compiler
from distutils.tests import support
from sysconfig import get_config_var, get_config_vars
from test.support import TESTFN, run_unittest, check_warnings

class SysconfigTestCase(support.EnvironGuard, unittest.TestCase):
    def setUp(self):
        super(SysconfigTestCase, self).setUp()
        self.makefile = None

    def tearDown(self):
        if self.makefile is not None:
            os.unlink(self.makefile)
        self.cleanup_testfn()
        super(SysconfigTestCase, self).tearDown()

    def cleanup_testfn(self):
        if os.path.isfile(TESTFN):
            os.remove(TESTFN)
        elif os.path.isdir(TESTFN):
            shutil.rmtree(TESTFN)

    def test_get_config_h_filename(self):
        config_h = sysconfig.get_config_h_filename()
        self.assertTrue(os.path.isfile(config_h), config_h)

    def test_get_python_lib(self):
        # XXX doesn't work on Linux when Python was never installed before
        #self.assertTrue(os.path.isdir(lib_dir), lib_dir)
        # test for pythonxx.lib?
        self.assertNotEqual(sysconfig.get_python_lib(),
                            sysconfig.get_python_lib(prefix=TESTFN))

    def test_get_config_vars(self):
        cvars = get_config_vars()
        self.assertIsInstance(cvars, dict)
        self.assertTrue(cvars)

    def test_srcdir(self):
        # See Issues #15322, #15364.
        srcdir = get_config_var('srcdir')

        self.assertTrue(os.path.isabs(srcdir), srcdir)
        self.assertTrue(os.path.isdir(srcdir), srcdir)

        if sysconfig.python_build:
            # The python executable has not been installed so srcdir
            # should be a full source checkout.
            Python_h = os.path.join(srcdir, 'Include', 'Python.h')
            self.assertTrue(os.path.exists(Python_h), Python_h)
            self.assertTrue(sysconfig._is_python_source_dir(srcdir))
        elif os.name == 'posix':
            self.assertEqual(
                os.path.dirname(sysconfig.get_makefile_filename()),
                srcdir)

    def test_srcdir_independent_of_cwd(self):
        # srcdir should be independent of the current working directory
        # See Issues #15322, #15364.
        srcdir = get_config_var('srcdir')
        cwd = os.getcwd()
        try:
            os.chdir('..')
            srcdir2 = get_config_var('srcdir')
        finally:
            os.chdir(cwd)
        self.assertEqual(srcdir, srcdir2)

    @unittest.skipUnless(get_default_compiler() == 'unix',
                         'not testing if default compiler is not unix')
    def test_customize_compiler(self):
        os.environ['AR'] = 'my_ar'
        os.environ['ARFLAGS'] = '-arflags'

        # make sure AR gets caught
        class compiler:
            compiler_type = 'unix'

            def set_executables(self, **kw):
                self.exes = kw

        comp = compiler()
        sysconfig.customize_compiler(comp)
        self.assertEqual(comp.exes['archiver'], 'my_ar -arflags')

    def test_parse_makefile_base(self):
        self.makefile = TESTFN
        fd = open(self.makefile, 'w')
        try:
            fd.write(r"CONFIG_ARGS=  '--arg1=optarg1' 'ENV=LIB'" '\n')
            fd.write('VAR=$OTHER\nOTHER=foo')
        finally:
            fd.close()
        d = sysconfig.parse_makefile(self.makefile)
        self.assertEqual(d, {'CONFIG_ARGS': "'--arg1=optarg1' 'ENV=LIB'",
                             'OTHER': 'foo'})

    def test_parse_makefile_literal_dollar(self):
        self.makefile = TESTFN
        fd = open(self.makefile, 'w')
        try:
            fd.write(r"CONFIG_ARGS=  '--arg1=optarg1' 'ENV=\$$LIB'" '\n')
            fd.write('VAR=$OTHER\nOTHER=foo')
        finally:
            fd.close()
        d = sysconfig.parse_makefile(self.makefile)
        self.assertEqual(d, {'CONFIG_ARGS': r"'--arg1=optarg1' 'ENV=\$LIB'",
                             'OTHER': 'foo'})

    @unittest.skipIf(get_config_var('EXT_SUFFIX') is None,
                     'EXT_SUFFIX required for this test')
    def test_SO_deprecation(self):
        self.assertWarns(DeprecationWarning,
                         get_config_var, 'SO')

    @unittest.skipIf(get_config_var('EXT_SUFFIX') is None,
                     'EXT_SUFFIX required for this test')
    def test_SO_value(self):
        with check_warnings(('', DeprecationWarning)):
            self.assertEqual(get_config_var('SO'),
                             get_config_var('EXT_SUFFIX'))

    @unittest.skipIf(get_config_var('EXT_SUFFIX') is None,
                     'EXT_SUFFIX required for this test')
    def test_SO_in_vars(self):
        vars = get_config_vars()
        self.assertIsNotNone(vars['SO'])
        self.assertEqual(vars['SO'], vars['EXT_SUFFIX'])

    def test_customize_compiler_before_get_config_vars(self):
        # Issue #21923: test that a Distribution compiler
        # instance can be called without an explicit call to
        # get_config_vars().
        with open(TESTFN, 'w') as f:
            f.writelines(textwrap.dedent('''\
                from distutils.core import Distribution
                config = Distribution().get_command_obj('config')
                # try_compile may pass or it may fail if no compiler
                # is found but it should not raise an exception.
                rc = config.try_compile('int x;')
                '''))
        p = subprocess.Popen([str(sys.executable), TESTFN],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True)
        outs, errs = p.communicate()
        self.assertEqual(0, p.returncode, "Subprocess failed: " + outs)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SysconfigTestCase))
    return suite


if __name__ == '__main__':
    run_unittest(test_suite())
