import unittest
from uniai_connector.matching import normalize,rank_customers

class MatchingTest(unittest.TestCase):
    def test_initials_and_punctuation(self):
        for query in ['AR Medical Store','A.R Medical Store','A. R. Medical Store','a r medical store']:
            self.assertEqual(normalize(query),'ar medical store')
    def test_ar_does_not_match_babar_or_popular(self):
        names=['Abu Bakar Medical Store','Babar Medical Store','Popular Medical Store','A.R Medical Store (Doctor Plaza)']
        rows=[dict(name=n,customer_name=n) for n in names]
        self.assertEqual([r['name'] for r in rank_customers('ar medical store',rows)],[names[-1]])
    def test_keep_real_ambiguity(self):
        rows=[dict(name='A',customer_name='A.R Medical Store East'),dict(name='B',customer_name='AR Medical Store West')]
        self.assertEqual(len(rank_customers('ar medical',rows)),2)
    def test_prefixes_require_three_characters(self):
        rows=[dict(name='Babar Medical Store',customer_name='Babar Medical Store')]
        self.assertEqual(rank_customers('ar medical',rows),[])
        self.assertEqual(len(rank_customers('bab medical',rows)),1)
