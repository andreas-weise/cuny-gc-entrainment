import unittest

import sys
sys.path.insert(0, '../')
import system_components as sc
import auxiliaries as aux

class TestDirectComponent(unittest.TestCase):
    
    def test_is_abstract_class(self):
        msg = ''
        try:
            test_comp = sc.DirectComponent(-1)
        except TypeError as e:
            msg = str(e)
        #testing this way because TypeError could also result from invalid input
        self.assertEqual(msg.find("Can't instantiate abstract class"), 0)

if __name__ == '__main__':
    unittest.main()
