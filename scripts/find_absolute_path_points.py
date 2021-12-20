#!/usr/bin/python

THRESH=0.07

import re
from lxml import etree
import sys
from decimal import Decimal
from collections import defaultdict
from math import sqrt

def _verify_segments(list_of_segments):
    for x in list_of_segments:
        assert(len(x) == 2) ## one move and one curve
        #_assert(len(x) == 1) ## one curve
        _assert(len(x[0][1]) >= 1) ## one or more points
        _assert(len(x[0][1][0]) == 2) ## a point
        assert(x[0][0] == 'M')
        _assert(x[1][0] in ('M','L','C'))

def _debugunless(foo):
    if not foo:
        pass
        import pdb; pdb.set_trace()

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
    smallenum = '(?:[-+]?)\d+e-\d+'
    d_string = re.sub(smallenum, '0', d_string)
    commandmatch = re.match(f"{command}(.*)", d_string)
    _assert(commandmatch)
    command = commandmatch.group(1)
    d_string = commandmatch.group(2)
    points = []
    prev_command = None

    while True:
        if prev_command in ('V','v','H','h') and re.match(f"\s*({num})\s*(.*)", d_string) and not re.match(f"\s*({num},{num})(.*)", d_string):
            if pointmatch:
                command = prev_command
        if command in ('V','v','H','h'):
            prev_command = command
            pointmatch = re.match(f"\s*({num})\s*(.*)", d_string)
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
            assert(move in ('m', 'M'))
        segments.append((move, points))
        assert(prev != d_string)
        if not d_string:
            break

    last_point = None

    start_point = None
    for segment in segments:
        (command, points) = segment
        if command in ('m', 'M'):
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
                if command == 'm':
                    command = 'l'
                else:
                    command = 'L'
                moveto = ('M', (last_point,))
            else:
                continue
        else:
            moveto = ('M', (last_point,))

        _assert(last_point[1]>1)
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
        elif command == 'C':
            assert((len(points)%3) == 0)
            for cnt in range(0, len(points)//3):
                triple_point = points[cnt*3:cnt*3+3]
                absolute_independent_segments.append((moveto, ('C', tuple(triple_point))))
                ## last segment, last command, points, third point
                last_point = absolute_independent_segments[-1][-1][1][2]
                moveto = ('M', (last_point,))
        elif command in ('z', 'Z'):
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

def _printable_dpath(path):
    ## Remove all the stupid extra M-commands
    new_path = [ path[0][0] ] + [segment[1] for segment in path]
    return " ".join([_printable_segment(segment) for segment in new_path])

def cut_paths(segments_by_start_point, junctions):
    prev_point = None
    start_point = None
    paths = []
    points_visited = set()
    while segments_by_start_point:
        if prev_point is None:
            ## must be a nicer way
            if junctions:
                start_point = junctions.__iter__().__next__()
                is_island = False
            else:
                start_point = segments_by_start_point.keys().__iter__().__next__()
                is_island = True
        else:
            distance_square=1<<31
            if [x for x in junctions if x in segments_by_start_point]:
                possible_starting_points = junctions
                is_island = False
            else:
                possible_starting_points = segments_by_start_point.keys()
                is_island = True
            for start_point_ in possible_starting_points:
                if not start_point_ in segments_by_start_point:
                    continue
                distance_square_ = 0
                for x in zip(start_point_, prev_point):
                    distance_square_ += (x[0]-x[1])**2
                if distance_square_ < distance_square:
                    distance_square = distance_square_
                    start_point = start_point_
        assert(start_point is not None)
        assert(start_point in segments_by_start_point)
        path = []
        prev_point = None
        while start_point in segments_by_start_point:
            if not segments_by_start_point[start_point]:
                import pdb; pdb.set_trace()
                ## something seriously wrong.  the path just stops out in nowhere
                segments_by_start_point.pop(start_point)
                continue
            if start_point in junctions and len(path)>0:
                paths.append(path)
                path = []
                prev_point = None
            next_segment = segments_by_start_point[start_point].pop()
            if not segments_by_start_point[start_point]:
                segments_by_start_point.pop(start_point)
            prev_point = start_point
            start_point = next_segment[-1][-1][-1]
            path.append(next_segment)
            points_visited.add(start_point)
            discarded_segments = set()
            for potentially_reversed_segment in segments_by_start_point[start_point]:
                if potentially_reversed_segment[-1][-1][-1] == prev_point:
                    discarded_segments.add(potentially_reversed_segment)
            for reversed_segment in discarded_segments:
                segments_by_start_point[start_point].remove(reversed_segment)
            if not segments_by_start_point[start_point]:
                segments_by_start_point.pop(start_point)
        print(len(segments_by_start_point))
        if len(path)>0:
            ## should not happen if file is containing only closed loop
            _debugunless(start_point in junctions or is_island)
            paths.append(path)
        else:
            import pdb; pdb.set_trace()
            print(f"something muffens at {start_point}")
    return paths

## not in use anymore
def rounded(point, num_decimals=3):
    return (round(point[0], num_decimals), round(point[1], num_decimals))

def sqdist(a, b):
    return (a[0]-b[0])**2+(a[1]-b[1])**2

def path_points(path):
    return [x[0][1][0] for x in path] + [ path[-1][-1][-1][-1] ]

def find_near_points(segments_by_points, paths=None, threshold=THRESH):
    """a simplification of path_conflicts"""
    points = list(segments_by_points.keys())
    if paths:
        paths_p = [path_points(p) for p in paths]
        paths_by_point = defaultdict(set)
        for path_i in range(0, len(paths_p)):
            for point in paths_p[path_i]:
                paths_by_point[point].add(path_i)

    movelist = {}
    ## arbitrary point
    ap = points[0]
    points.sort(key=lambda x: sqdist(x, ap))
    i1 = 0
    while i1 < len(points):
        i2 = i1+1
        orig_dist = sqdist(points[i1], ap)
        dst = points[i1]
        if dst in movelist:
            dst = movelist[dst]
        #if points[i2][0]>100:
            #import pdb; pdb.set_trace()
        while ( i2 < len(points) and
                sqrt(sqdist(points[i2], ap))-sqrt(orig_dist) < threshold):
            if sqdist(points[i2], points[i1])<threshold**2:
                #if sqdist(points[i2], (Decimal('238.66615'),Decimal('201.26455')))<1:
                    #import pdb; pdb.set_trace()
                ## Two points that are on the same path should not be merged
                if not paths or paths_by_point[points[i1]] != paths_by_point[points[i2]]:
                    movelist[points[i2]] = dst
            i2 += 1
        i1 += 1
    return movelist


def path_conflicts(a, b, threshold=THRESH):
    """The original data contains duplicated paths.  A lot of effort has
    been put into removing true duplicates, this method attempts to
    remove arts of paths containing almost overlapping lines.  (Two
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
        return None

    for p in points:
        p.sort(key=lambda x: sqdist(x, start))
    i1=1
    i2=1
    ## common starting point
    _assert(points[0][0] == points[1][0])
    movelist = {}
    last_near_points = None
    last_counters = (0,0)
    while i1<len(points[0]) and i2<len(points[1]):
        if sqdist(points[0][i1], points[1][i2]) < threshold**2:
            if points[0][i1] != points[1][i2]:
                #if points[0][i1] not in junctions:
                movelist[points[0][i1]] = points[1][i2]
                #else:  movelist[points[1][i2]] = points[0][i1]
            last_near_points = (points[0][i1], points[1][i2])
            last_counters = (i1, i2)
        else:
            if i1>last_counters[0]+2 and i2>last_counters[0]+2:
                return movelist
        if sqdist(points[0][i1], start) < sqdist(points[1][i2], start):
            i1 += 1
        elif sqdist(points[0][i1], start) > sqdist(points[1][i2], start):
            i2 += 1
        else:
            if i1+1<len(points[0]) and i2+1<len(points[1]):
                if sqdist(points[0][i1+1], start) < sqdist(points[1][i2+1], start):
                    i1 += 1
                elif sqdist(points[0][i1+1], start) > sqdist(points[1][i2+1], start):
                    i2 += 1
                else:
                    i1+=1
                    i2+=1
            elif i1+1<len(points[0]):
                i1 += 1
            else:
                i2 += 1
        
    return movelist

def save_paths(continent, paths, filename='/tmp/test.svg'):
    g = continent.find('{http://www.w3.org/2000/svg}g')
    i=0
    elements = []
    for path in paths:
        i+=1
        path_element = etree.Element('{http://www.w3.org/2000/svg}path')
        path_element.set('d', _printable_dpath(path))
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
        pl = segments_by_point[point]
        for i1 in range(0, len(pl)):
            for i2 in range(i1+1, len(pl)):
                a=pl[i1] ; b = pl[i2]
                if ((a[0][0][0] == b[0][0][0] and a[-1][-1][-1] == b[-1][-1][-1]) or
                    (a[0][0][0] == b[-1][-1][-1] and a[-1][-1][-1] == b[0][0][0])):
                    blacklist.add(b)
    return (segments_by_points_to_set(segments_by_point) - blacklist)

def segments_replaced(segments_by_point, movelist):
    all_segments = segments_by_points_to_set(segments_by_point)
    return_list = set()
    ## first, move the starting point of all affected segments
    for segment in all_segments:
        start = segment[0][1][0]
        stop = segment[-1][-1][-1]
        if start in movelist or stop in movelist:
            start = movelist.get(start, start)
            end = movelist.get(stop, stop)
            segment = (('M', (start,)),(segment[1][0], segment[1][1][0:-1]+(end,)))
        return_list.add(segment)
    return return_list

def segments_replaced_verybuggy(segments_by_point, movelist):
    debug_removed = set()
    debug_added = set()
    for m in movelist:
        assert m[0] not in [x[1] for x in movelist]
    all_segments = segments_by_points_to_set(segments_by_point)
    ## debug
    for x in all_segments:
        assert(x[0][1][0] in segments_by_point)
        assert(x[-1][-1][-1] in segments_by_point)
        assert(x in segments_by_point[x[-1][-1][-1]])
        assert(x in segments_by_point[x[0][1][0]])
    for (src, dst) in movelist:
        assert(src not in [x[1] for x in movelist])
        assert(dst not in [x[0] for x in movelist])
        if not src in segments_by_point:
            ## due to two-pass solution
            continue
        bad_segments = segments_by_point.pop(src)
        for bad_segment in bad_segments:
            if not bad_segment in all_segments:
                ## it was probably already removed
                ## TODO: by now we're running this function twice to catch the cases where both start and end is in the shitlist
                #_assert(bad_segment in debug_removed)
                continue
            all_segments.remove(bad_segment)
            debug_removed.add(bad_segment)
            try:
                foo = bad_segment[0][1][0]
            except:
                import pdb; pdb.set_trace()
            if bad_segment[0][1][0] == src:
                new_segment = (('M', (dst,)), bad_segment[1])
            if bad_segment[-1][-1][-1] == src:
                new_segment = (bad_segment[0], (bad_segment[1][0], bad_segment[1][1][0:-1]+(dst,)))
            if new_segment[0][0][0] != new_segment[-1][-1][-1]:
                all_segments.add(new_segment)
            assert new_segment[0][1][0] != src
            assert new_segment[-1][-1][-1] != src
            #_assert(new_segment[-1][-1][-1] not in [x[0] for x in movelist]) ## will fail on first iteration
            #_assert(new_segment[0][1][0] not in [x[0] for x in movelist])
            assert bad_segment not in all_segments
            debug_added.add(new_segment)
    ## debug
    #for x in all_segments:
        #for m in movelist:
            #_assert(x[0][1][0] != m[0])
            #_assert(x[-1][-1][-1] != m[0])
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
            if len(segments_by_point[point])>2:
                import pdb; pdb.set_trace()
            segments_by_point.pop(point)
    return segments_by_points_to_set(segments_by_point)

def find_segment_points(segments):
    segments_by_start_point = defaultdict(list)
    segments_by_point = defaultdict(list)
    no_reverse_dup_segments_by_point = defaultdict(list)
    junctions = set()

    debug_point1 = (Decimal('205.13'),Decimal('130.839'))
    debug_point2 = (Decimal('204.449'),Decimal('132.213'))
    debug_segments1 = [x for x in segments if sqdist(x[0][1][0], debug_point1)<0.5 or sqdist(x[-1][-1][-1], debug_point1)<0.5]
    debug_segments = [x for x in segments if sqdist(x[0][1][0], debug_point2)<0.5 or sqdist(x[-1][-1][-1], debug_point2)<0.5 and x in debug_segments1]

    for segment in segments:
        #if segment in debug_segments:
            #import pdb; pdb.set_trace()
        start_point = segment[0][1][0]
        end_point = segment[-1][-1][-1]
        if start_point == end_point:
            ## this may happen due to "snapped" points.
            continue
        #if (rounded(end_point) == rounded(fake_junction) or
            #rounded(start_point) == rounded(fake_junction)):
            #import pdb; pdb.set_trace()
        for potentially_duplicated_segment in segments_by_start_point[start_point]:
            if potentially_duplicated_segment[-1][-1][-1] == end_point:
                ## this segment is a duplicate, probably with different bezier points or different command, but most likely it should be discarded
                #print(f"almost-duplicates(?): {potentially_duplicated_segment} {segment} - dropping the last one?")
                segment = None
        if not segment:
            continue
        reverse_dup = False
        for potentially_reversed_segment in segments_by_start_point[end_point]:
            if potentially_reversed_segment[-1][-1][-1] == start_point:
                reverse_dup = True
                #print(f"reverse-duplicate(?): {potentially_reversed_segment} <--->  {segment} - one of them should be dropped, but which one?")
                ## the remove-reverse-segment-logic has been moved to the cut-path function
        if not segment:
            continue
        if not reverse_dup:
            no_reverse_dup_segments_by_point[start_point].append(segment)
            no_reverse_dup_segments_by_point[end_point].append(segment)
        segments_by_point[start_point].append(segment)
        segments_by_point[end_point].append(segment)
        for point in (start_point, end_point):
            #if len(segments_by_point[point])>2:
            if len(no_reverse_dup_segments_by_point[point])>2:
                junctions.add(point)
        segments_by_start_point[start_point].append(segment)
    print(f'num points and num segments by point and by start point: {len(segments_by_point)} {len(segments_by_start_point)} {sum([len(x) for x in segments_by_point.values()])} {sum([len(x) for x in segments_by_start_point.values()])}')
    #import pdb; pdb.set_trace()
    ## no - segments may contain near-duplicates or reversed duplicates
    #_assert(sum([len(x) for x in segments_by_start_point.values()]) == len(segments))
    ## should not happen if file is containing only closed loop
    #_debugunless(not [x for x in segments_by_point if len(segments_by_point[x])<2])

    cnt1=0
    cnt2=0
    cnt3=0
    for x in segments_by_point:
        ## orphans - non-closed loop starting or ending here
        if len(segments_by_point[x])==1:
            junctions.add(x)
            import pdb; pdb.set_trace()
        if x in junctions:
            if not len(segments_by_point[x])>2:
                cnt1 += 1
        else:
            if not len(segments_by_point[x]) in (2,3,4):
                cnt2 += 1
            if not len(segments_by_start_point[x]) in (1,2):
                cnt3 +=1

    ## should not happen if file is containing only closed loop
    #_debugunless(cnt1+cnt2+cnt3 == 0)

    return(segments_by_start_point, segments_by_point, junctions)

def find_micro_path(paths):
    for path in paths:
        if len(path) == 1:
            pp = path_points(path)
            _assert(len(pp)==2)
            if sqdist(*pp)<THRESH**2:
                return pp

def _remove_near_dupes_recalc(paths, segments_by_point, movelist):
    segments = segments_replaced(segments_by_point, movelist)
    segments_by_start_point, segments_by_point, junctions = find_segment_points(segments)
    paths = cut_paths(segments_by_start_point, junctions)
    print(f"junctions3: {junctions}")
    return (segments_by_start_point, segments_by_point, junctions, paths)

def remove_near_dupes(paths, segments_by_point):
    ## TODO: refactor
    
    movelist = find_near_points(segments_by_point, threshold=THRESH/5)
    if movelist:
        (segments_by_start_point, segments_by_point, junctions, paths) = _remove_near_dupes_recalc(paths, segments_by_point, movelist)
    movelist2 = find_near_points(segments_by_point, paths, threshold=THRESH*3)
    if movelist2:
        (segments_by_start_point, segments_by_point, junctions, paths) = _remove_near_dupes_recalc(paths, segments_by_point, movelist2)
    movelist3 = find_near_duplicated_paths(paths)
    if movelist3:
        (segments_by_start_point, segments_by_point, junctions, paths) = _remove_near_dupes_recalc(paths, segments_by_point, movelist3)
    if movelist or movelist2 or movelist3:
        return (segments_by_start_point, segments_by_point, junctions, paths)

    ## TODO: we need one more method for finding overlapping paths.  Need to simply calculate a bitmap for each path, and find groups of points that are nearby each other.
    
    return None

def find_near_duplicated_paths(paths):
    ## TODO: this can easily yield false negatives
    for i1 in range(0, len(paths)):
        for i2 in range(i1+1, len(paths)):
            ## this one should not return anything as path_conflicts have been
            ## superceded by find_near_points, but let's verify that ...
            _assert(not path_conflicts(paths[i1], paths[i2]))
            
            start1 = paths[i1][0][0][1][0]
            start2 = paths[i2][0][0][1][0]
            end1 = paths[i1][-1][-1][-1][-1]
            end2 = paths[i2][-1][-1][-1][-1]
            #debug_point =  (Decimal('238.66615'), Decimal('201.26453'))
            #if (min(sqdist(start1, debug_point),
                    #sqdist(end1, debug_point))<1 and
                #min(sqdist(start2, debug_point),
                    #sqdist(end2, debug_point))<1):
                #import pdb; pdb.set_trace()
            if ((start1 == start2 and end1 == end2) or
                (start1 == end2 and end1 == start2)):
                ## Two paths with the same start point and end point.
                ## This may be perfectly legitimate, in case a country has exactly
                ## two borders.
                ## If the two paths are going in the same direction but with
                ## slightly different points, then one of them should be removed
                path1 = path_points(paths[i1])
                path2 = path_points(paths[i2])
                if path1[0] == path2[-1]:
                    path2.reverse()
                sum_sqdist = 0
                cnt = 0
                movelist = {}
                j1 = 1
                j2 = 1
                while j1 < len(path1)-1 or j2 < len(path2)-1:
                    dist0 = sqdist(path1[j1], path2[j2])

                    #debug_point = (Decimal('204.44864'),Decimal('132.21252'))
                    #if sqdist(debug_point, path1[j1])<1 or sqdist(debug_point, path2[j2])<1:
                        #import pdb; pdb.set_trace()
                    
                    sum_sqdist += dist0
                    cnt += 1

                    movelist[path1[j1]] = path2[j2]

                    ## one or both the counters should be moved forward
                    dist1 = sqdist(path1[j1+1], path2[j2]) if j1 < len(path1)-1 else 1<<31
                    dist2 = sqdist(path1[j1], path2[j2+1]) if j2 < len(path2)-1 else 1<<31
                    dist3 = sqdist(path1[j1+1], path2[j2+1]) if j1 < len(path1)-1 and j2 < len(path2)-1 else 1<<31
                    mindist = min(dist1, dist2, dist3)

                    if mindist == dist1:
                        j1 += 1
                    elif mindist == dist2:
                        j2 += 1
                    else:
                        j1 += 1
                        j2 += 1
                        
                ## TODO: the risk of false (negatives/postives) here may be big, consider
                ## two long straight lines where one line has two points and
                ## the other line has three points ... should probably either
                ## increase the threshold or use a smarter algorithm
                if sum_sqdist / (cnt+2) < (THRESH*32)**2:
                    return movelist
    return None

def main(filename):
    segments = set()
    blacklist = []

    with open(filename, 'br') as f:
        continent = etree.XML(f.read())
    g = continent.find('{http://www.w3.org/2000/svg}g')
    for path in g.findall('{http://www.w3.org/2000/svg}path'):
        segments.update(set(find_absolute_path_segments(path.get('d'))))
        g.remove(path)

    #(segments_by_start_point, segments_by_point, junctions) = find_segment_points(segments)
    #segments = evict_start_end_duplicate_segments(segments_by_point)
    print(f"num segments originally: {len(segments)}")
    (segments_by_start_point, segments_by_point, junctions) = find_segment_points(segments)
    
    print(f"num segments after segment finder: {len(segments_by_points_to_set(segments_by_point))}")
    print(f"num segments (should be the same): {sum([len(x) for x in segments_by_start_point.values()])}")

    paths = cut_paths(segments_by_start_point, junctions)

    ## TODO: this code is maybe not needed?
    while True:
        mp = find_micro_path(paths)
        if not mp:
            break
        ## TODO: where does this micro path come from?
        #import pdb; pdb.set_trace()
        segments = segments_replaced(segments_by_point, {mp[0]: mp[1]})
        segments_by_start_point, segments_by_point, junctions = find_segment_points(segments)
        paths = cut_paths(segments_by_start_point, junctions)

    print(f"junctions1: {junctions}")
    foo = True
    while foo:
        foo = remove_near_dupes(paths, segments_by_point)
        if foo:
            (segments_by_start_point, segments_by_point, junctions, paths) = foo
    print(f"num segments after further deduplication: {len(segments_by_points_to_set(segments_by_point))}")

    save_paths(continent, paths)
    return(paths, junctions)


if __name__ == '__main__':
    main(sys.argv[1])

