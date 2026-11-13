"""Offline tests / Pruebas sin conexión."""
import unittest
from fixture_schema import summarize

class FixtureSchemaTests(unittest.TestCase):
    def test_no_sensitive_data_in_report(self):
        source=[{"_id":"secret-unique-id","_rev":"3-secret","type":"plain","path":"Private/Family.md","data":"my private note","children":["private-id"],"password":"my-password"}]
        result=str(summarize(source))
        for secret in ("secret-unique-id","Private/Family.md","my private note","private-id","my-password","password"):
            self.assertNotIn(secret,result)
    def test_all_docs_rows(self):
        data={"rows":[{"id":"one","doc":{"type":"leaf","data":"private"}},{"id":"two","doc":{"type":"plain","children":[]}}]}
        result=summarize(data)
        self.assertEqual(result["document_count"],2)
    def test_rejects_large_batch(self):
        with self.assertRaises(ValueError):
            summarize([{}]*101)
    def test_rejects_unexpected_object(self):
        with self.assertRaises(ValueError):
            summarize({"secret":"x"})

if __name__=="__main__":
    unittest.main()
