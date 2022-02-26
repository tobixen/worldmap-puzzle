import find_absolute_path_points as p
from unittest import TestCase
from decimal import Decimal
from collections import defaultdict

def _line_segment(point1, point2):
    """
    I regret a bit using this complicated segment format
    """
    return p.Segment((('M', (point1,)), ('L', (point2,))))

class UnitTests(TestCase):
    def test_angnum(self):
        prev_point = (10,10)
        my_point = (20,10)
        next_points = [(2,9), (30,20), (1,9), (30,10), (10,10), (10,0), (30,0), (20,0)]
        next_points.sort(key=lambda next_point: p._angnum(prev_point, my_point, next_point))
        self.assertEqual(next_points, [(1,9), (2,9), (10,0), (20,0), (30,0), (30,10), (30,20), (10,10)])

    def test_outline(self):
        ## two partly overlapping rectangles
        path1 = "m 10,10 h 50 v 50 50 h -50 z"
        path2 = "M 60,60 v 50 50 h 50 v -100 Z"

        ## four squares
        square = [
            "M 10,10   h 10 v 10 h -10 v -10 Z",
            "M 20,20  h 10 v 10 h -10 v -10 Z",
            "M 10,20  h 10 v 10 h -10 v -10 Z",
            "M 20,10 h 10 v 10 h -10 v -10 Z"]

        ## squares and a rectangle (with extra points) and an island
        rectangles1 = [
            "M 10,10   h 10 v 10 h -10 v -10 Z",
            "M 20,20  h 10 v 10 h -10 v -10 Z",
            "M 21,21  h 8 v 8 h -8 v -8 Z",
            "M 10,20  h 10 v 10 h -10 v -10 Z",
            "M 20,10 h 10 h 10 v 10 h -10 h -10 v -10 Z"]
        
        segments = set()
        for path in (path1, path2):
            segments.update(set(p.find_absolute_path_segments(path)))
        (segments_by_start_point, segments_by_point, junctions) = p.find_segment_points(segments)
        paths = p.cut_paths(segments_by_start_point, junctions)
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(junctions), 2)
        outlines = p.find_outlines(paths, junctions)
        self.assertEqual(len(outlines), 1)
        self.assertEqual(outlines[0][0][0][1][0], outlines[0][-1][-1][-1][-1])
        self.assertFalse((('M', ((Decimal('60'), Decimal('110')),)), ('L', ((Decimal('60'), Decimal('60')),))) in outlines[0])
        self.assertFalse((('M', ((Decimal('60'), Decimal('60')),)), ('L', ((Decimal('60'), Decimal('110')),))) in outlines[0])
        self.assertTrue(
            (('M', ((Decimal('60'), Decimal('60')),)), ('L', ((Decimal('110'), Decimal('60')),))) in outlines[0] or
            (('M', ((Decimal('110'), Decimal('60')),)), ('L', ((Decimal('60'), Decimal('60')),))) in outlines[0])
        self.assertTrue(
            (('M', ((Decimal('10'), Decimal('10')),)), ('L', ((Decimal('10'), Decimal('110')),))) in outlines[0] or
            (('M', ((Decimal('10'), Decimal('110')),)), ('L', ((Decimal('10'), Decimal('10')),))) in outlines[0])


        segments = set()
        for path in square:
            segments.update(set(p.find_absolute_path_segments(path)))
        (segments_by_start_point, segments_by_point, junctions) = p.find_segment_points(segments)
        paths = p.cut_paths(segments_by_start_point, junctions)
        self.assertEqual(len(paths), 8)
        self.assertEqual(len(junctions), 5)
        outlines = p.find_outlines(paths, junctions)
        self.assertEqual(len(outlines), 1)

        segments = set()
        for path in rectangles1:
            segments.update(set(p.find_absolute_path_segments(path)))
        (segments_by_start_point, segments_by_point, junctions) = p.find_segment_points(segments)
        paths = p.cut_paths(segments_by_start_point, junctions)
        self.assertEqual(len(paths), 9)
        self.assertEqual(len(junctions), 5)
        outlines = p.find_outlines(paths, junctions)
        self.assertEqual(len(outlines), 2)
        
    def test_find_near_points(self):
        some_points = ((0,0),(1,1),(1,0),(0,1),(100,100),(0.5,0.5))
        some_other_points = {(0,0.5), (2,1),(101,100)}
        some_points_skewed1 = ((x, y+0.0001) for x,y in some_points)
        some_points_skewed2 = ((x+0.0001, y+0.0001) for x,y in some_points)
        some_points_skewed3 = ((x+0.0001, y) for x,y in some_points)
        reverse_point1 = lambda x, y: (-x, -y)
        reverse_point2 = lambda x, y: (-x, y)
        reverse_point3 = lambda x, y: (x, -y)
        segments_by_point = {}
        num = 0
        num_duplicates = 0
        for pointlist in (some_points, some_points_skewed1, some_points_skewed2, some_points_skewed3):
            for point in pointlist:
                for pnt in (point, reverse_point1(*point), reverse_point2(*point), reverse_point3(*point)):
                    ## the current algoritm does not care about the values in this dict,
                    ## setting it to 1 is easiest
                    if pnt in segments_by_point:
                        num_duplicates += 1 ## (0,0), +/- (x,0), +/- (0,x) ... 5 in total
                    else:
                        num += 1
                    segments_by_point[pnt] = 1
                    
        ## now segments_by_point should have a lot of nearly duplicated values
        assert(num_duplicates == 15)
        assert(num == 6*4*4-num_duplicates)
        assert(len(segments_by_point) == num)

        ## Lets add some unique values to the mix
        for pnt in some_other_points:
            segments_by_point[pnt] = 1
        
        movelist = p.find_near_points(segments_by_point)
        
        ## For inspecting the results of the find ...
        targets = set(movelist.values())
        not_moved = set([x for x in segments_by_point if x not in movelist])

        ## the "not moved" list should be the targets plus the unique points in some_other_points
        self.assertEqual(targets.union(some_other_points), not_moved)

        ## there should be no overlapping between the targets and the some_other_points
        self.assertTrue(not targets.intersection(some_other_points))

    def test_reverse_path(self):
        my_path = [
            p.Segment((('M', ((Decimal('10'), Decimal('20')),),), ('C', (Decimal('12'),(Decimal('15')), (Decimal('14'),(Decimal('15')), (Decimal('20'),(Decimal('15'))))))),),
            p.Segment((('M', ((Decimal('20'), Decimal('15')),),), ('L', ((Decimal('20'), Decimal('40')),))),),
            p.Segment((('M', ((Decimal('20'), Decimal('40')),),), ('L', ((Decimal('30'), Decimal('60')),))))]

        reverse = p.reverse_path(my_path)
        self.assertNotEqual(reverse, my_path)
        self.assertEqual(p.reverse_path(reverse), my_path)

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
    def test_four_squares(self):
        paths, junctions, outlines, continent = p.main('./testD.svg')
        self.assertEqual(len(paths), 8)
        self.assertEqual(len(junctions), 5)

    def test_reverse_island(self):
        paths, junctions, outlines, continent = p.main('./testC.svg')
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(junctions), 0)
        rev = p.reverse_path(paths[0])
        self.assertEqual(p.reverse_path(rev), paths[0])

    def test_island_outline(self):
        paths, junctions, outlines, continent = p.main('./testC.svg')
        self.assertEqual(len(paths), 1)
        self.assertEqual(len(junctions), 0)
        ## this can be removed in the future ... p.main will eventually do
        ## the outline stuff by itself
        outlines = p.find_outlines(paths, junctions)
        assert(len(outlines)==1)
        self.assertEqual(outlines[0], paths[0])
    
    def test_simple_semiduplicate(self):
        ## in this file, two segments have same starting and ending
        ## position ((60,60),(60,30)), one of them is a bezier curve.
        ## Those two segments should be collapsed into one.
        paths, junctions, outlines, continent = p.main('./test2.svg')
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(junctions), 2)
        self.assertTrue((Decimal('60'), Decimal('60')) in junctions)
        self.assertTrue((Decimal('60'), Decimal('30')) in junctions)
        ## TODO: verify that the duplicated line is gone

    ## TODO: this test is broken
    #def test_inaccurate_duplicates(self):
        ## in this file, two segments have same starting and ending
        ## position ((60,60),(60,30)), one of them is a bezier curve.
        ## Those two segments should be collapsed into one.
        #paths, junctions, outlines, continent = p.main('./test3.svg')
        #self.assertEqual(len(paths), 4)
        #self.assertEqual(len(junctions), 2)
        #self.assertTrue((Decimal('60'), Decimal('60')) in junctions)
        #self.assertTrue((Decimal('60'), Decimal('30')) in junctions)

    def test_one_duplicated_line(self):
        paths, junctions, outlines, continent = p.main('./test5.svg')
        #self.assertEqual(len(paths), 3)
        #self.assertEqual(len(junctions), 2)
        self.assertTrue((Decimal('40'), Decimal('20')) in junctions)
        self.assertTrue((Decimal('40'), Decimal('40')) in junctions)
        
    def test_one_reverse_duplicated_line(self):
        paths, junctions, outlines, continent = p.main('./test6.svg')
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(junctions), 2)
        self.assertTrue((Decimal('40'), Decimal('20')) in junctions)
        self.assertTrue((Decimal('40'), Decimal('40')) in junctions)

    def test_almost_duplicated_lines1(self):
        ## as test6, but s/20/19.999/ in one corner of one path
        ## this should still be considered as two territories with one shared border,
        ## and not as two territories touching in one point
        paths, junctions, outlines, continent = p.main('./test8.svg')
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(junctions), 2)
        
    def test_almost_duplicated_lines2(self):
        ## as test6, but s/20/19.999/ in one path
        ## this should still be considered as two territories with one shared border,
        ## and not as two indepent islands
        paths, junctions, outlines, continent = p.main('./test7.svg')
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(junctions), 2)
        
    def test_north_africa(self):
        paths, junctions, outlines, continent = p.main('./test4.svg')
        self.assertEqual(len(paths), 3)
        self.assertEqual(len(junctions), 2)

    def test_more_of_africa(self):
        paths, junctions, outlines, continent = p.main('./test9.svg')
        self.assertEqual(len(junctions), 6)
        self.assertEqual(len(paths), 9)

    def test_parts_of_europe(self):
        paths, junctions, outlines, continent = p.main('./testA.svg')
        self.assertEqual(len(junctions), 4)
        self.assertEqual(len(paths), 6)
        self.assertEqual(len(outlines), 1)
        

    ## TODO: can testB .. testF be cleaned away?

class ContinentTests(TestCase):
    def test_australia(self):
        paths, junctions, outlines, continent = p.main('../common/maptiles-spare-pieces/australia.svg')
        self.assertTrue(p.rounded((Decimal('412.96204'), Decimal('289.27004'))) in [p.rounded(x) for x in junctions])
        self.assertTrue(p.rounded((Decimal('394.52484'), Decimal('234.60159'))) in [p.rounded(x) for x in junctions])
        self.assertEqual(len(junctions), 2)
        self.assertEqual(len(paths), 8)
        
    def test_africa(self):
        paths, junctions, outlines, continent = p.main('../common/maptiles-spare-pieces/africa.svg')
        self.assertEqual(len(junctions), 8)
        self.assertEqual(len(paths), 13)

    def test_europe(self):
        paths, junctions, outlines, continent = p.main('../common/maptiles-spare-pieces/europe.svg')
        ## TODO: fix numbers below
        ## 3 islands
        self.assertEqual(len(junctions), 8)
        self.assertEqual(len(paths), 15)

    def test_north_america(self):
        ## TODO: fix the bug
        paths, junctions, outlines, continent = p.main('../common/maptiles-spare-pieces/north-america.svg')
        self.assertEqual(len(junctions), 14)
        self.assertEqual(len(paths), 22)

    def test_south_america(self):
        paths, junctions, outlines, continent = p.main('../common/maptiles-spare-pieces/south-america.svg')
        self.assertEqual(len(junctions), 6)
        self.assertEqual(len(paths), 9)

    def test_asia(self):
        ## TODO: verify the numbers below
        paths, junctions, outlines, continent = p.main('../common/maptiles-spare-pieces/asia.svg')
        #self.assertEqual(len(junctions), 18)
        self.assertEqual(len(junctions), 20)
        #self.assertEqual(len(junctions), 22)
        self.assertEqual(len(paths), 31)
        #self.assertEqual(len(paths), 34)
