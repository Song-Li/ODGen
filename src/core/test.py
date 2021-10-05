import unittest
#from src.core.opgen import OPGen

class BasicTests(unittest.TestCase):

    def setUp(self):
        """Call before every test case."""
        self.opgen = OPGen()

    def tearDown(self):
        """Call after every test case."""
        pass

    def os_command_test(self):
        """
        run the os command test
        """
        file_loc = "./tests/os_command.js"
        opgen.test_file(file_loc, vul_type='os_command')

    def testB(self):
        """test case B"""
        assert (1 == 1) == True
        return 0

    def testC(self):
        """test case C"""
        assert foo.baz() == "blah", "baz() not returning blah correctly"

def run_tests():
    unittest.main(argv=[''],verbosity=0)
