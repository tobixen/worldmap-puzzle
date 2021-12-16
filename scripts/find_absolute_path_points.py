#!/usr/bin/python

import re
from lxml import etree
import sys
from decimal import Decimal

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

    for segment in segments:
        (command, points) = segment
        if command == 'm':
            #absolute_independent_segments.append((('M', (points[0],)),))
            if last_point is None:
                last_point = points[0]
            else:
                last_point = _sum(last_point, points[0])
            start_point = last_point
            if len(points) > 1:
                points.pop(0)
                command = 'l'
                moveto = ('M', (last_point,))
            else:
                continue
        else:
            moveto = ('M', (last_point,))

        _assert(last_point[1]>10)

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
            ## first segment, first command (move), points, first (and only) point
            absolute_independent_segments.append((moveto, ('L', (start_point,))))
            #absolute_independent_segments.append((('L', (absolute_independent_segments[0][0][1][0],)),))
            _verify_segments(absolute_independent_segments)
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

def cut_paths(g, global_segments_by_start_point):
    prev_point = (0,0)
    start_point = (0,0)
    paths = []
    points_visited = set()
    while global_segments_by_start_point:
        distance_square=1<<31
        for start_point_ in global_segments_by_start_point:
            distance_square_ = 0
            for x in zip(start_point_, prev_point):
                distance_square_ += (x[0]-x[1])**2
            if distance_square_ < distance_square:
                distance_square = distance_square_
                start_point = start_point_
        assert(start_point != (0,0))
        assert(start_point in global_segments_by_start_point)
        path = []
        while start_point in global_segments_by_start_point:
            next_segment = global_segments_by_start_point[start_point].pop()
            if not global_segments_by_start_point[start_point]:
                global_segments_by_start_point.pop(start_point)
            prev_start_point = start_point
            start_point = next_segment[-1][-1][-1]
            if prev_start_point in points_visited and start_point in points_visited:
                break
            path.append(next_segment)
            if start_point in points_visited:
                break
            points_visited.add(start_point)
        _assert(len(path)>0)
        print(len(global_segments_by_start_point))
        paths.append(path)
    return paths

if __name__ == '__main__':
    global_segments = set()
    global_segments_by_start_point = {}

    with open(sys.argv[1], 'br') as f:
        continent = etree.XML(f.read())
    g = continent.find('{http://www.w3.org/2000/svg}g')
    for path in g.findall('{http://www.w3.org/2000/svg}path'):
        global_segments.update(set(find_absolute_path_segments(path.get('d'))))
        g.remove(path)

    for segment in global_segments:
        start_point = segment[0][1]
        assert(len(start_point) == 1)
        start_point = start_point[0]
        if not start_point in global_segments_by_start_point:
            global_segments_by_start_point[start_point] = []
        global_segments_by_start_point[start_point].append(segment)

    paths = cut_paths(g, global_segments_by_start_point)

    i=0
    for path in paths:
        i+=1
        path_element = etree.Element('{http://www.w3.org/2000/svg}path')
        path_element.set('d', _printable_segments2(path))
        path_element.set('style', 'fill:none;stroke:#ff0000;stroke-width:0.25')
        path_element.set('id', f'line{i:02d}')
        g.append(path_element)
    
    with open('/tmp/test.svg', 'bw') as f:
        f.write(etree.tostring(continent))

