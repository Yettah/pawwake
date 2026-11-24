import unittest
from character_portability import parse_backup,memory_fields
class PortabilityTests(unittest.TestCase):
    def test_dedup(self):
        row={'content':' 你好 ','layer':2}
        self.assertEqual(parse_backup({'format':'pawwake-character','version':1,'memories':[row,row]}),[('你好',2)])
    def test_invalid_layer(self):
        with self.assertRaises(ValueError): memory_fields({'content':'a','layer':True})
    def test_reject_foreign_fields(self):
        with self.assertRaises(ValueError): memory_fields({'content':'a','layer':2,'character_id':'other'})
    def test_version(self):
        with self.assertRaises(ValueError): parse_backup({'format':'pawwake-character','version':2,'memories':[]})
