import unittest
from os import remove
import requests

import sys
sys.path.insert(0, '../')
import remote_tts as rem

class TestSynthesize(unittest.TestCase):
    
    def setUp(self):
        self.in_fname = '../../tmp/ssml_test.xml'
        self.ssml_str = (
            '<?xml version="1.0" encoding="UTF-8" ?>\n'
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"\n'
            '       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
            '       xsi:schemaLocation="http://www.w3.org/2001/10/synthesis '
            'http://www.w3.org/TR/speech-synthesis/synthesis.xsd"\n'
            '       xml:lang="en-US">\n'
            'This is a test.\n'
            '</speak>'
            )
        self.ssml_file = open(self.in_fname, 'w')
        self.ssml_file.write(self.ssml_str)
        self.ssml_file.flush()
        self.ssml_file.close()

        self.in_fname2 = '../../tmp/text_test.txt'
        self.text_str = 'This is a test.'
        self.text_file = open(self.in_fname2, 'w')
        self.text_file.write(self.text_str)
        self.text_file.flush()
        self.text_file.close()

        self.out_fname = '../../tmp/test.wav'

    def test_synthesize_ssml_file_local_mary(self):
        rem.synthesize_file(self.in_fname, self.out_fname, '127.0.0.1', 59125,
                            rem.TTS_TYPE_MARY, 'en_US', 'SSML')
        #if no exception was raised then the function finished successfully
        self.assertTrue(True)

    def test_synthesize_ssml_str_local_mary(self):
        rem.synthesize_str(self.ssml_str, self.out_fname, '127.0.0.1', 59125,
                           rem.TTS_TYPE_MARY, 'en_US', 'SSML')
        #if no exception was raised then the function finished successfully
        self.assertTrue(True)

    def test_synthesize_faulty_ssml_str_local_mary(self):
        ssml_str = self.ssml_str[:-1]
        self.assertRaises(requests.exceptions.RequestException,
                          rem.synthesize_str, ssml_str, self.out_fname,
                          '127.0.0.1', 59125, rem.TTS_TYPE_MARY, 'en_US',
                          'SSML')

    def test_synthesize_text_file_local_mary(self):
        rem.synthesize_file(self.in_fname2, self.out_fname, '127.0.0.1', 59125,
                            rem.TTS_TYPE_MARY, 'en_US', 'TEXT')
        #if no exception was raised then the function finished successfully
        self.assertTrue(True)

    def test_synthesize_text_str_local_mary(self):
        rem.synthesize_str(self.text_str, self.out_fname, '127.0.0.1', 59125,
                           rem.TTS_TYPE_MARY, 'en_US', 'TEXT')
        #if no exception was raised then the function finished successfully
        self.assertTrue(True)

    def tearDown(self):
        remove(self.in_fname)
        remove(self.in_fname2)
        remove(self.out_fname)


if __name__ == '__main__':
    unittest.main()
