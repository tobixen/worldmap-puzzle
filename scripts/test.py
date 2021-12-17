import find_absolute_path_points as p
from unittest import TestCase

class FunctionalTests(TestCase):
    def test_main(self):
        paths, junctions = p.main('../common/maptiles-spare-pieces/australia/australia.svg')
        import pdb; pdb.set_trace()
        self.assertTrue((Decimal('412.96204'), Decimal('289.27004')) in junctions)
        self.assertTrue((Decimal('394.52484'), Decimal('234.60159')) in junctions)
        self.assertEqual(len(junctions), 2)
        self.assertEqual(len(paths), 8)
