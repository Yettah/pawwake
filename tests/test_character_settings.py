import unittest
from character_settings import validate
class SettingsTest(unittest.TestCase):
    def test_inherit(self): self.assertEqual(validate({'chat_model':'','temperature':None}),{})
    def test_values(self): self.assertEqual(validate({'memory_enabled':False,'temperature':0}),{'memory_enabled':False,'temperature':0})
    def test_reject(self):
        for value in ({'api_base_url':'http://localhost'},{'temperature':True},{'max_tokens':0},{'prompt_mode':'bad'}):
            with self.assertRaises(ValueError): validate(value)
