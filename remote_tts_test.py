import unittest
import remote_tts as rem
from os import remove
import requests

class TestSendSSML(unittest.TestCase):
    
    def setUp(self):
        self.in_fname = 'send_ssml_test.xml'
        self.out_fname = 'send_ssml_test.wav'
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

    def test_send_ssml_file_to_local_mary(self):
        rem.send_ssml_file(self.in_fname, self.out_fname, '127.0.0.1', 59125,
                           rem.TTS_TYPE_MARY, 'en_US')
        #if no exception was raised then the function finished successfully
        self.assertTrue(True)

    def test_send_ssml_str_to_local_mary(self):
        rem.send_ssml_str(self.ssml_str, self.out_fname, '127.0.0.1', 59125,
                          rem.TTS_TYPE_MARY, 'en_US')
        #if no exception was raised then the function finished successfully
        self.assertTrue(True)

    def test_send_faulty_ssml_to_local_mary(self):
        ssml_str = self.ssml_str[:-1]
        self.assertRaises(requests.exceptions.RequestException,
                          rem.send_ssml_str, ssml_str, self.out_fname,
                          '127.0.0.1', 59125, rem.TTS_TYPE_MARY, 'en_US')

    def tearDown(self):
        remove(self.in_fname)
        remove(self.out_fname)


if __name__ == '__main__':
    unittest.main()
