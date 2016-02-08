import unittest
import auxiliaries as aux

class TestAuxiliaries(unittest.TestCase):
    
    def test_is_int(self):
        self.assertTrue(aux.is_int(42, 'test'))
        self.assertTrue(aux.is_int(3//2, 'test'))
        self.assertRaises(TypeError, aux.is_int, 3.5, 'test')
        self.assertRaises(TypeError, aux.is_int, '42', 'test')
        self.assertRaises(TypeError, aux.is_int, None, 'test')

    def test_is_float(self):
        self.assertTrue(aux.is_float(4.2, 'test'))
        self.assertTrue(aux.is_float(3/2, 'test'))
        self.assertRaises(TypeError, aux.is_float, 3, 'test')
        self.assertRaises(TypeError, aux.is_float, '4.2', 'test')
        self.assertRaises(TypeError, aux.is_float, None, 'test')

    def test_is_pos(self):
        self.assertTrue(aux.is_pos(5, 'test'))
        self.assertTrue(aux.is_pos(3.1415, 'test'))
        self.assertTrue(aux.is_pos(float('inf'), 'test'))
        self.assertRaises(ValueError, aux.is_pos, -5, 'test')
        self.assertRaises(ValueError, aux.is_pos, float('nan'), 'test')
        self.assertRaises(TypeError, aux.is_pos, 'abc', 'test')
        self.assertRaises(TypeError, aux.is_pos, None, 'test')

    def test_is_in_list(self):
        self.assertTrue(aux.is_in_list( 2, (1, 2, 3), 'test'))
        self.assertTrue(aux.is_in_list( 'c', 'abc', 'test'))
        self.assertTrue(aux.is_in_list( 'a', (3, 'a', .5), 'test'))
        self.assertTrue(aux.is_in_list( .5, (3, 'a', .5), 'test'))
        
        lst = [1,2,3]
        lst_of_lsts = [[1,2,3],[4,5,6]]
        self.assertTrue(aux.is_in_list( lst, lst_of_lsts, 'test'))

        dct = {}
        key = 'key'
        value = 'value'
        dct[key] = value
        self.assertTrue(aux.is_in_list( key, dct, 'test'))
        self.assertRaises(ValueError, aux.is_in_list, value, dct, 'test')

        self.assertRaises(ValueError, aux.is_in_list, 4, (1, 2, 3), 'test')
        self.assertRaises(ValueError, aux.is_in_list, 3.14, (3, 3.1), 'test')
        self.assertRaises(ValueError, aux.is_in_list, float('nan'), (3, 3.1),
                          'test')
        self.assertRaises(ValueError, aux.is_in_list, 'a', ('b', 3, .5), 'test')

    def test_is_less_or_equal(self):
        self.assertTrue(aux.is_less_or_equal(42, 1776, 'test1', 'test2'))
        self.assertTrue(aux.is_less_or_equal(-3.14, 42, 'test1', 'test2'))
        self.assertTrue(aux.is_less_or_equal(1337, 1337, 'test1', 'test2'))
        self.assertTrue(aux.is_less_or_equal('abc', 'def', 'test1', 'test2'))
        self.assertTrue(aux.is_less_or_equal([1,5], [1,7], 'test1', 'test2'))
        
        self.assertRaises(ValueError, aux.is_less_or_equal, 15, 5, 'test1',
                          'test2')
        self.assertRaises(ValueError, aux.is_less_or_equal, 3.14, -7, 'test1',
                          'test2')
        self.assertRaises(TypeError, aux.is_less_or_equal, 5, 'a', 'test1',
                          'test2')

if __name__ == '__main__':
    unittest.main()
