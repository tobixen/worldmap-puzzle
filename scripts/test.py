import find_absolute_path_points as p
from unittest import TestCase
from decimal import Decimal
from collections import defaultdict

def _line_segment(point1, point2):
    """
    I regret a bit using this complicated segment format
    """
    return (('M', (point1,)), ('L', (point2,)))

class UnitTests(TestCase):
    def test_find_absolute_path_segments(self):
        expected_results = {
            'M 10,20 l 10,20': [(('M', ((Decimal('10'), Decimal('20')),)), ('L', ((Decimal('20'), Decimal('40')),)))],
            'm 10,20 10,20 10,20': [(('M', ((Decimal('10'), Decimal('20')),)), ('L', ((Decimal('20'), Decimal('40')),))), (('M', ((Decimal('20'), Decimal('40')),)), ('L', ((Decimal('30'), Decimal('60')),)))],
            'm 10,20 v 5 10,20': [(('M', ((Decimal('10'), Decimal('20')),)), ('L', ((Decimal('10'), Decimal('25')),))), (('M', ((Decimal('10'), Decimal('25')),)), ('L', ((Decimal('20'), Decimal('45')),)))],
            'm 10,20 v 5 10 20 30': [(('M', ((Decimal('10'), Decimal('20')),)), ('L', ((Decimal('10'), Decimal('25')),))), (('M', ((Decimal('10'), Decimal('25')),)), ('L', ((Decimal('10'), Decimal('35')),))), (('M', ((Decimal('10'), Decimal('35')),)), ('L', ((Decimal('10'), Decimal('55')),))), (('M', ((Decimal('10'), Decimal('55')),)), ('L', ((Decimal('10'), Decimal('85')),)))]
        }
        for d_string in expected_results:
            self.assertEqual(p.find_absolute_path_segments(d_string), expected_results[d_string])

    def test_segments_replaced(self):
        """The purpose of the segments_replaced function is to move the
        points in a segments to "snap" them with nearby points, making
        deduplication possible.  However, it should also be possible
        to use it to move a square 80 pixels to the right
        """
        segments_by_point = defaultdict(list)
        square = [(20,20), (40,20), (40,40), (20,40), (20,20)]
        for i in range(0,4):
            from_ = square[i]
            to = square[i+1]
            segment = _line_segment(square[i], square[i+1])
            segments_by_point[from_].append(segment)
            segments_by_point[to].append(segment)
        moves = {}
        for point in square:
            moves[point] = p._sum(point, (80,0))
        moved_segments = p.segments_replaced(segments_by_point, moves)
        expected_segments = {
            (('M', ((100, 20),)), ('L', ((120, 20),))),
            (('M', ((120, 20),)), ('L', ((120, 40),))),
            (('M', ((120, 40),)), ('L', ((100, 40),))),
            (('M', ((100, 40),)), ('L', ((100, 20),)))}
        self.assertEqual(expected_segments, moved_segments)

class FunctionalTests(TestCase):
    def test_australia(self):
        paths, junctions = p.main('../common/maptiles-spare-pieces/australia/australia.svg')
        self.assertTrue((Decimal('412.96204'), Decimal('289.27004')) in junctions)
        self.assertTrue((Decimal('394.52484'), Decimal('234.60159')) in junctions)
        self.assertEqual(len(junctions), 2)
        self.assertEqual(len(paths), 8)

    def test_simple_semiduplicate(self):
        ## in this file, two segments have same starting and ending
        ## position ((60,60),(60,30)), one of them is a bezier curve.
        ## Those two segments should be collapsed into one.
        paths, junctions = p.main('./test2.svg')
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(junctions), 2)
        self.assertTrue((Decimal('60'), Decimal('60')) in junctions)
        self.assertTrue((Decimal('60'), Decimal('30')) in junctions)
        ## TODO: verify that the duplicated line is gone
        
    def test_inaccurate_duplicates(self):
        ## in this file, two segments have same starting and ending
        ## position ((60,60),(60,30)), one of them is a bezier curve.
        ## Those two segments should be collapsed into one.
        paths, junctions = p.main('./test3.svg')
        #self.assertEqual(len(paths), 4)
        #self.assertEqual(len(junctions), 2)
        self.assertTrue((Decimal('60'), Decimal('60')) in junctions)
        self.assertTrue((Decimal('60'), Decimal('30')) in junctions)
        
    def test_north_africa(self):
        ## in this file, two segments have same starting and ending
        ## position ((60,60),(60,30)), one of them is a bezier curve.
        ## Those two segments should be collapsed into one.
        paths, junctions = p.main('./test4.svg')
        import pdb; pdb.set_trace()
        #self.assertEqual(len(paths), 4)
        #self.assertEqual(len(junctions), 2)
        self.assertTrue((Decimal('60'), Decimal('60')) in junctions)
        self.assertTrue((Decimal('60'), Decimal('30')) in junctions)
        
