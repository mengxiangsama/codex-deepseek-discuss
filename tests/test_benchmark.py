"""No model credentials, inference or network required."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('compare', Path(__file__).parents[1] / 'benchmarks/compare.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

class BenchmarkTests(unittest.TestCase):
    def test_business_cases(self):
        suite = b.read(b.ROOT / 'orders.json')
        expected = [('pending',9,0), ('paid',9,0), ('closed',10,1), ('closed',10,0),
                    ('closed',10,1), ('closed',10,2), ('paid',9,0), ('paid',9,0)]
        for case, values in zip(suite['cases'], expected, strict=True):
            self.assertEqual(b.reference(case['events']), dict(zip(['status','stock','refunds'],values)))

    def test_exact_answer_shape(self):
        suite = {'cases':[{'id':'a','events':[]}]}
        with self.assertRaises(ValueError):
            b.grade(suite, {})
        self.assertFalse(b.grade(suite, {'a':{'status':'pending','stock':9,'refunds':False}})[0]['passed'])
        self.assertFalse(b.grade(suite, {'a':{'status':'paid','stock':9,'refunds':0}})[0]['passed'])

    def test_unknown_cost_and_unpaired(self):
        r = {'kind':'model_run','arm':'single','suite_sha256':'abc','scores':[{'passed':True}],
             'elapsed_seconds':1,'cost_usd':None}
        report = b.summarize([r])[0]
        self.assertFalse(report['comparable'])
        self.assertIsNone(report['arms']['single']['total_cost_usd'])
        other = {**r, 'arm':'dual', 'cost_usd':0.02}
        self.assertTrue(b.summarize([r, other])[0]['comparable'])

    def test_reject_offline_checks(self):
        with self.assertRaises(ValueError):
            b.summarize([{'kind':'offline_check'}])

    def test_invalid_numbers(self):
        for value in [-1, float('nan'), float('inf'), True]:
            with self.assertRaises(ValueError):
                b.number(value, 'cost')

if __name__ == '__main__':
    unittest.main()
