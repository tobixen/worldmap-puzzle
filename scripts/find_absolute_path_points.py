#!/usr/bin/python

SQTHRESH=0.001

import re
from lxml import etree
import sys
from decimal import Decimal
from collections import defaultdict

def _verify_segments(list_of_segments):
    for x in list_of_segments:
        assert(len(x) == 2) ## one move and one curve
        #_assert(len(x) == 1) ## one curve
        _assert(len(x[0][1]) >= 1) ## one or more points
        _assert(len(x[0][1][0]) == 2) ## a point
        assert(x[0][0] == 'M')
        _assert(x[1][0] in ('M','L','C'))


def _assert(foo):
    if not foo:
        import pdb; pdb.set_trace()
        assert(foo)

## I somehow feel a bit stupid ... most likely there is a better way to do
## this through standard python libraries
def _sum(point, vector):
    """Adds a vector to a point"""
    return tuple([p+v for (p,v) in zip(point, vector)])

def _text2tuple(point):
    xy = point.split(',')
    return tuple([Decimal(x) for x in xy])

def _d_cmd_points(d_string):
    """
    Reads a d-string.
    Returns a one-character command, points argument to the command and the rest of the string
    The HhVv commands are replaced with lL-commands
    """
    command = '\s*([a-zA-Z])\s*'
    num = '(?:[-+]?)\d+(?:\.\d+)?'
    commandmatch = re.match(f"{command}(.*)", d_string)
    _assert(commandmatch)
    command = commandmatch.group(1)
    d_string = commandmatch.group(2)
    points = []

    while True:
        if command in ('V','v','H','h'):
            pointmatch = re.match(f"\s*({num})(.*)", d_string)
        else:
            pointmatch = re.match(f"\s*({num},{num})(.*)", d_string)
        if not pointmatch:
            break
        if command == 'v':
            points.append((0,Decimal(pointmatch.group(1))))
            command = 'l'
        elif command == 'h':
            points.append((Decimal(pointmatch.group(1)), 0))
            command = 'l'
        elif command == 'H':
            points.append((Decimal(pointmatch.group(1)), None))
            command = 'L'
        elif command == 'V':
            points.append((None,Decimal(pointmatch.group(1))))
            command = 'L'
        else:
            points.append(_text2tuple(pointmatch.group(1)))
        d_string = pointmatch.group(2)
    points = [point for point in points]
    return(command, points, d_string)

def find_absolute_path_segments(d_string):
    """
    Takes a d-string and parses it.
    Converts all relative points to absolute points
    Makes all segments into "canonical segments" starting with the M-command
    """
    segments = []
    absolute_independent_segments = []
    
    while True:
        prev = d_string
        (move, points, d_string) = _d_cmd_points(d_string)
        if not segments:
            assert(move == 'm')
        segments.append((move, points))
        assert(prev != d_string)
        if not d_string:
            break

    last_point = None

    start_point = None
    for segment in segments:
        (command, points) = segment
        if command == 'm':
            #absolute_independent_segments.append((('M', (points[0],)),))
            if last_point is None:
                last_point = points[0]
            else:
                last_point = _sum(last_point, points[0])
            if start_point is None:
                start_point = last_point
            else:
                import pdb; pdb.set_trace()
            if len(points) > 1:
                points.pop(0)
                command = 'l'
                moveto = ('M', (last_point,))
            else:
                continue
        else:
            moveto = ('M', (last_point,))

        _assert(last_point[1]>10)
        _assert(start_point is not None)

        if command == 'l':
            for point in points:
                lineto = _sum(last_point, point)
                absolute_independent_segments.append((moveto, ('L', (lineto,))))
                #absolute_independent_segments.append((('L', (lineto,)),))
                last_point = lineto
                moveto = ('M', (last_point,))
        elif command == 'L':
            for point in points:
                if point[0] is None:
                    point = (last_point[0], point[1])
                if point[1] is None:
                    point = (point[0], last_point[1])
                absolute_independent_segments.append((moveto, ('L', (point,))))
                #absolute_independent_segments.append((('L', (lineto,)),))
                last_point = point
                moveto = ('M', (last_point,))
        elif command == 'c':
            assert((len(points)%3) == 0)
            for cnt in range(0, len(points)//3):
                triple_point = tuple([_sum(last_point, point) for point in points[cnt*3:cnt*3+3]])
                absolute_independent_segments.append((moveto, ('C', triple_point)))
                #absolute_independent_segments.append((('C', triple_point),))
                ## last segment, last command, points, third point
                last_point = absolute_independent_segments[-1][-1][1][2]
                moveto = ('M', (last_point,))
        elif command == 'z':
            assert not points
            assert start_point is not None
            if start_point != last_point:
                absolute_independent_segments.append((moveto, ('L', (start_point,))))
                _verify_segments(absolute_independent_segments)
                last_point = start_point
            start_point = None
        else:
            raise NotImplementedError(f"move command {command}")
        _verify_segments(absolute_independent_segments)

    return absolute_independent_segments
    #return absolute_independent_segments[0:43]

def _printable_segment(x):
    (command, points) = x
    try:
        points = [ "{0},{1}".format(*point) for point in points ]
    except Exception:
        import pdb; pdb.set_trace()
    return f'{command} {" ".join(points)}'

def _printable_segments(segments):
    return " ".join([_printable_segment(segment) for segment in segments])

def _printable_segments2(set_of_independent_segments):
    return " ".join([_printable_segments(segments) for segments in set_of_independent_segments])

def find_a_start_point(segments_by_start_point):
    for x in segments_by_start_point:
        if len(segments_by_start_point[x])>1:
            return x
    return x

def cut_paths(segments_by_start_point, junctions):
    prev_point = None
    start_point = None
    paths = []
    points_visited = set()
    while segments_by_start_point:
        if prev_point is None:
            start_point = find_a_start_point(segments_by_start_point)
        else:
            distance_square=1<<31
            for start_point_ in segments_by_start_point:
                distance_square_ = 0
                for x in zip(start_point_, prev_point):
                    distance_square_ += (x[0]-x[1])**2
                if distance_square_ < distance_square:
                    distance_square = distance_square_
                    start_point = start_point_
        assert(start_point is not None)
        assert(start_point in segments_by_start_point)
        path = []
        while start_point in segments_by_start_point:
            if not segments_by_start_point[start_point]:
                segments_by_start_point.pop(start_point)
                break
            if start_point in junctions and len(path)>0:
                paths.append(path)
                path = []
            next_segment = segments_by_start_point[start_point].pop()
            if not segments_by_start_point[start_point]:
                segments_by_start_point.pop(start_point)
            prev_start_point = start_point
            start_point = next_segment[-1][-1][-1]
            path.append(next_segment)
            points_visited.add(start_point)
        print(len(segments_by_start_point))
        if len(path)>0:
            paths.append(path)
        else:
            print(f"something muffens at {start_point}")
    return paths

## not in use anymore
def rounded(point, num_decimals=3):
    return (round(point[0], num_decimals), round(point[1], num_decimals))

def sqdist(a, b):
    return (a[0]-b[0])**2+(a[1]-b[1])**2

def path_points(path):
    return [x[0][1][0] for x in path] + [ path[-1][-1][-1][-1] ]

def path_conflicts(a, b, sqthreshold=SQTHRESH):
    """The original data contains duplicated paths.  A lot of effort has
    been put into removing true duplicates, this method attempts to
    remove parts of paths containing almost overlapping lines.  (Two
    paths also should not cross each other (this is not tested for
    currently).

    Algorithm:
    * Find a common junction point 
    * if none exist, assume the paths aren't overlapping - this may not always be true though
    * sort the points in the paths by distance to the common junction point
    * go through the sorted points and check the distance between them
    * if several successive points are too close to each other,  consider the points from the b-path broken and add them to a blacklist
    * return blacklist
    * if paths diverge, we need to anchor the non-blacklisted parts of path b in a new junction point on path a
    * we need to eliminate the offending segments from the segment list, add a new anchor segment, and rerun quite some of the logic (on the outside of this function)
    """
    points = [path_points(x) for x in (a,b)]
    start = None

    ## find a common junction, if any
    for combo in ((0,0), (0,-1), (-1,-1), (-1,0)):
        if points[0][combo[0]] == points[1][combo[1]]:
            start = points[0][combo[0]]
            break
    if not start:
        return (None, None)

    for p in points:
        p.sort(key=lambda x: sqdist(x, start))
    i1=1
    i2=1
    ## common starting point
    _assert(points[0][0] == points[1][0])
    blacklist = []
    last_near_points = None
    last_counters = (0,0)
    while i1<len(points[0]) and i2<len(points[1]):
        if sqdist(points[0][i1], points[1][i2]) < sqthreshold:
            if last_near_points:
                blacklist.append(last_near_points[1])
            last_near_points = (points[0][i1], points[1][i2])
            last_counters = (i1, i2)
        else:
            if i1>last_counters[0]+2 and i2>last_counters[0]+2:
                return (blacklist, last_near_points)
        if sqdist(points[0][i1], start) < sqdist(points[1][i2], start):
            i1 += 1
        else:
            i2 += 1
    return (blacklist, last_near_points)

def save_paths(continent, paths, filename='/tmp/test.svg'):
    g = continent.find('{http://www.w3.org/2000/svg}g')
    i=0
    elements = []
    for path in paths:
        i+=1
        path_element = etree.Element('{http://www.w3.org/2000/svg}path')
        path_element.set('d', _printable_segments2(path))
        path_element.set('style', 'fill:none;stroke:#ff0000;stroke-width:0.25')
        path_element.set('id', f'line{i:02d}')
        elements.append(path_element)
        g.append(path_element)
    
    with open(filename, 'bw') as f:
        f.write(etree.tostring(continent))

    for path in elements:
        g.remove(path)

def evict_start_end_duplicate_segments(segments_by_point):
    """
    let's assert we don't have any closed loops involving nothing but two bezier segments
    """
    blacklist = set()
    for point in segments_by_point:
        for a in segments_by_point[point]:
            for b in segments_by_point[point]:
                if a == b:
                    continue
                if ((a[0][0][0] == b[0][0][0] and a[-1][-1][-1] == b[-1][-1][-1]) or
                    (a[0][0][0] == b[-1][-1][-1] and a[-1][-1][-1] == b[0][0][0])):
                    blacklist.add(b)
    return (segments_by_points_to_set(segments_by_point) - blacklist)

def segments_replaced(segments_by_point, src, dst):
    all_segments = segments_by_points_to_set(segments_by_point)
    bad_segments = segments_by_point.pop(src)
    for bad_segment in bad_segments:
        all_segments.remove(bad_segment)
        try:
            foo = bad_segment[0][1][0]
        except:
            import pdb; pdb.set_trace()
        if bad_segment[0][1][0] == src:
            new_segment = (('M', (dst,)), bad_segment[1])
        else:
            new_segment = (bad_segment[0], (bad_segment[1][0], bad_segment[1][1][0:-1]+(dst,)))
        if new_segment[0][0][0] != new_segment[-1][-1][-1]:
            all_segments.add(new_segment)
    return all_segments

def segments_by_points_to_set(segments_by_point):
    segments_set = set()
    for segments in segments_by_point.values():
        for segment in segments:
            segments_set.add(segment)
    return segments_set

def remove_blacklisted_segments(segments_by_point, blacklist):
    for point in blacklist:
        if point in segments_by_point:
            segments_by_point.pop(point)
    return segments_by_points_to_set(segments_by_point)

def find_segment_points(segments):
    segments_by_start_point = defaultdict(list)
    segments_by_point = defaultdict(list)
    junctions = set()
    for segment in segments:
        start_point = segment[0][1][0]
        end_point = segment[-1][-1][-1]
        for potentially_duplicated_segment in segments_by_start_point[start_point]:
            if potentially_duplicated_segment[-1][-1][-1] == end_point:
                ## this segment is a duplicate, probably with different bezier points or different command, but most likely it should be discarded
                print(f"almost-duplicates(?): {potentially_duplicated_segment} {segment} - dropping the last one")
                #segment = None
        if not segment:
            continue
        for potentially_reversed_segment in segments_by_start_point[end_point]:
            if potentially_reversed_segment[0][1][0] == end_point:
                ## this segment is a duplicate, but in the reversed direction
                print(f"reverse-duplicate(?): {potentially_reversed_segment} {segment} - dropping the last one")
                #segment = None
        if not segment:
            continue
        segments_by_point[start_point].append(segment)
        segments_by_point[end_point].append(segment)
        for point in (start_point, end_point):
            if len(segments_by_point[point])>2:
                junctions.add(point)
        segments_by_start_point[start_point].append(segment)
    return(segments_by_start_point, segments_by_point, junctions)

def find_micro_path(paths):
    for path in paths:
        if len(path) == 1:
            pp = path_points(path)
            _assert(len(pp)==2)
            if sqdist(*pp)<SQTHRESH:
                return pp

def remove_near_dupes(paths, segments_by_point):
    for i1 in range(0, len(paths)):
        for i2 in range(i1+1, len(paths)):
            blacklist,last_points = path_conflicts(paths[i1], paths[i2])
            if blacklist: # or last_points:
                segments = remove_blacklisted_segments(segments_by_point, blacklist)
                segments_by_start_point, segments_by_point, junctions = find_segment_points(segments)
                print(f"junctions2: {junctions}")

                segments = segments_replaced(segments_by_point, last_points[0], last_points[1])
                segments_by_start_point, segments_by_point, junctions = find_segment_points(segments)
                paths = cut_paths(segments_by_start_point, junctions)
                print(f"junctions3: {junctions}")
                return (segments_by_start_point, segments_by_point, junctions, paths)
    return None

if __name__ == '__main__':
    segments = set()
    blacklist = []

    with open(sys.argv[1], 'br') as f:
        continent = etree.XML(f.read())
    g = continent.find('{http://www.w3.org/2000/svg}g')
    for path in g.findall('{http://www.w3.org/2000/svg}path'):
        segments.update(set(find_absolute_path_segments(path.get('d'))))
        g.remove(path)

    (segments_by_start_point, segments_by_point, junctions) = find_segment_points(segments)
    #segments = evict_start_end_duplicate_segments(segments_by_point)
    #(segments_by_start_point, segments_by_point, junctions) = find_segment_points(segments)

    print(f"num segments: {sum([len(x) for x in segments_by_start_point.values()])}")

    paths = cut_paths(segments_by_start_point, junctions)

    ## TODO: this code is maybe not needed?
    while True:
        mp = find_micro_path(paths)
        if not mp:
            break
        import pdb; pdb.set_trace()
        segments = segments_replaced(segments_by_point, mp[0], mp[1])
        segments_by_start_point, segments_by_point, junctions = find_segment_points(segments)
        paths = cut_paths(segments_by_start_point, junctions)

    print(f"junctions1: {junctions}")
    foo = True
    while foo:
        foo = remove_near_dupes(paths, segments_by_point)
        if foo:
            (segments_by_start_point, segments_by_point, junctions, paths) = foo

    save_paths(continent, paths)
