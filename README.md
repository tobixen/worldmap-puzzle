# World map puzzle

The details here are to be kept wrapped until the 24th of December.  If you read this after the 24th of December, please nag on me to post photos of the finished products as well as additional details and usage instructions.

## Files

Things are a bit messy at the moment ...

## Scripts

You should not need to care about anything in the script directory, but in case you wonder ...

The project is based on a svg file where every "territority" is a closed curve object.  This causes the laser to double-cut for the borders shared between two territories, this is undesirable.  I thought it would be a relatively trivial job to create a small and simple ad-hoc script to turn it into open non-duplicated line segments.  Right.  There were tons of problems, certainly including that many country borders were imperfectly drawn in the original file (two neighbouring countries, in theory one country border, but in practice two borders with different set of points).  Add some time stress, beer drinking while debugging, very late night sessions and it exploded into a horrendus spaghetti monster script.  It sort of works now, but I had to hand-edit the source map file to get all the junctions correct.  I've also hand-edited it to make the "bridge" across the Magellan strait wider, otherwise that map piece will be very fragile.  `common/maptiles-spare-pieces/all.svg` is the authorative source file.  `common/maptiles.svg` is generated from this one.  `common/maptiles-spare-pieces/*/*.svg` is partly generated through the `splitout.py` script.  They have not been re-generated after the last edits to `all.svg` (TODO!).