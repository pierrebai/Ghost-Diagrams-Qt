#!/usr/bin/env python

#    Copyright (C) 2004 Paul Harrison
#    Copyright (C) 2017 Pierre Baillargeon
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""  Ghost Diagrams

     This program takes sets of tiles that connect together in certain
     ways, and looks for the patterns these tiles imply. The patterns
     are often surprising.


     This software is currently somewhat alpha.

  Tile set specification:

     A tile set specification is a list of up to 8-, 6- or 4-character strings,
     corresponding to a hexagonal or square grid, respectively. For example,
     B-Aa-- b--Aa- represent two hexagonal tiles.

     Each character represents a tile edge. Letters (abcd, ABCD)
     match with their opposite case. Numbers match with themselves.
     Dashes represent no connection and dot match with anything.

     Missing characters are assumed to be dashes; the longest tile in the set
     decides if a square, hexagonal or octogonal grid is used.

     A tile specification can be multiplied by a number to make it
     that much likely to be selected. Multiplication by a number between
     zero and one decreases the likelyhood that the tile will be selected.

     A number of extra parameters can also be supplied:

         border : True/False : draw tile borders or not
         fill : True/False : fill tile or not with colors
         thickness : the thickness of the border
         width : minimum width of diagram
         height : minimum height of diagram
         background : the background color
         foreground : the foreground color (used for borders)
         colors : a list of colors : tile-1-color,tile-2-color... (no spaces between colors)
         grid : True/False : draw a grid or not
         labels : True/False : draw labels for each tile under diagram
         name : name of the tile set
         knot : shot knots on the tiles

     eg B-Aa-- b--Aa- width=1000 height=1000 thickness=0.5 colors=[000,000,fff,f00]

  TODO: don't backtrack areas outside current locus
        (difficulty: accidentally creating disconnected islands)

  TODO: (blue sky) 3D, third dimension == time
"""

import sys, os, random, math, functools, collections, optparse
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets


# ========================================================================
# Some cool tile sets people have found

catalogue = [
    "dD--4- 4--4 4a-A-4 aA a--A",
    "13-333 33---- 3-----",
    "3-3--3- 33-3---- 33------",
    "4-4--4--",
    "dDdDDD ddD--- D-4---",
    "111111 11111 11--1-",
    "a2A2 A222",
    "b-2-B- B----b-- b-----B name=snakes-and-ladders",
    "3--2--22 22-1---- 2------- name=plains-forest",
    "d--1D- d----D name=zap",
    "bDBB bB-- d-b-",
    "111-1 11-1 1-11 11",
    "aa-1 A--1 1-1-",
    "aaAA-A aa--a- aAA---",
    "4-4----- 444",
    "4-4-4-- 444",
    "a-3-3-A- 333----- a--A",
    "d-DBb- c---D- d-C---",
    "cccC CCC-",
    "DA13 d-3- a---",
    "111111 111-1- 1-1---",
    "11---1-- 1-1",
    "1111 441 111",
    "333--- 3--2--",
    "322---  232-- 3--3 2--2",
    "322---  232--",
    "323--- 3--2 232--",
    "333- 11-- 3--1",
    "a-A1 111- A11- 1---",
    "444- 4-4- 4--3",
    "aa2- A-4- a---",
    "aa--A--- aa----A- A-------",
    "3333-- aA3--3 3-----",
    "B222-- b2-2-2 22----",
    "bbbB/0 bBBB/f border=0",
    "ddDD dDdD dD",
    "dDc3 c-3 3C 3",
    "dD4 4-4 4a4A aA a-A",
    "dD4 4-4 4a-A aA Aa a-A",
    "dD4 4-4 4a4A aA Aa a-A",
    "Dd-cA d-D a-C",
    "d4-Dd d-D DD",
    "d3-3-- D-D",
    "d-D-4 d--D 44",
    "d-D-3 dD 3",
    "d-AD a--A a---A aa-A", # Counter-(?),
    "CcDdC cC-c C",
    "cCCcCC cccC c-C--C",
    "CcCc CcC-c c-C",
    "CCCc 3Ca-A 3--c c",
    "cCc-C cC-c-C",
    "cC-cC*3/f c-c-4*3/f C/f name=SSSS background=0 grid=0 foreground=d labels=0",
    "cc-c C-C-c",
    "cC-a-A a-A",
    "cABa aCAb aA aCA acA name=trains",
    "c44444 444444 4C44 c--4/f C--4/f border=0",
    "c414*5 4444*5 C4*5 4",
    "C332 c33 33C name=Alternance",
    "C-dDc CC-C ccC",
    "c-c-C cC-C C-c name=Circles",
    "c-c-C C-c C---c name=Corridor",
    "bC--B-*7/0 B/f c---b-/0 border=0 name=Labyrinth",
    "bBbBBB bb b---B",
    "BbbB b-BBB bb",
    "BbB-1 b",
    "Bbb- B--- BBb- name=Carvings",
    "bbb BB",
    "bB1 b--B--",
    "bb-bb BB B--B",
    "B-Aa b--Aa",
    "b-22 B--2 b",
    "b--b-b BbB",
    "acAC adBD bcBD bdAC",
    "acaACA acbBCB bcaBCB bcbACA",
    "abA B-C B-c B-D B-d",
    "ab-A-- B--C B--c B--D B--d",
    "AaAaaa --1-Aa A",
    "aaaa11 a 1 A A--A*10 A--a*3",
    "AaAa--",
    "aAaA-- bB bAaB",
    "AAaa-- a--A--",
    "aaaA a2AA name=Walls",
    "aAa3 3A 3a 3",
    "aaA-aA A---a A-a A",
    "Aaa A1A a-1AAa",
    "aA1--- AA- a--2",
    "Aa-Cc c C",
    "aa-aa/fff AA/fff A--A/fff grid=0 border=0 thickness=0.3 background=2",
    "aA-a2- 2A 2--A",
    "AA-A a-a-a-",
    "aA---- AaAa--",
    "a44A 4-4 Aa B-4b  bB name=PCB",
    "A44444 a4---4 4-4",
    "a4-4A- 4-4 aA a--A 4Dd name=Arteries",
    "A222 222- a--1",
    "a2--A a2-A2",
    "a-AA-A a-a",
    "A-A-a a-a",
    "A-A-a a--a",
    "a-A-a A",
    "a-A Aaa--A",
    "a-2a2 A---A 2",
    "a-1-A a--A",
    "A-1-1 a1---B b--1",
    "A--ab B-ab A--a B--b ABd--D name=Tree",
    "a--aa- AA",
    "a--a-- aAA-A",
    "a--4-- 4-4 A441",
    "a---4 a4-44A 4A",
    "a----- a-AA",
    "4A4a --a4 -A-B --Ab",
    "44B4D dbB4b 44D-d 44",
    "444444 4-4--3 4-3--3 44--4",
    "4444 c4-4 C--4 4",
    "44 11--4",
    "42-2 22 2-2",
    "33Aa/000 -33-Aa/000 background=fff foreground=888 border=0 grid=0",
    "33Aa -33-Aa",
    "33333 33",
    "33333 3-3",
    "3333-- name=triangles labels=1",
    "3333-- 333-3 33",
    "3322-- 2--2*10 name=two-sizes labels=1",
    "31--1 111 11",
    "3-3-3- 33",
    "2ddDDD/0d0 2d2d2/f60 dDDDd/0b0 foreground=0a0 name=flowers border=0",
    "22222a A2222",
    "222221 222223 name=two-zones",
    "222221 222",
    "22-22 22",
    "21221 221 2-2",
    "212111 1-2",
    "2-222 2---B2 b--2",
    "1B1B a-A bA ab-B",
    "141--- 4--4 1-1",
    "11111 1",
    "1111-- 1-1",
    "1111 1",
    "111",
    "1-1-1 2--12",
    "1-1-11-- 1--1 1-1",
]


# =========================================================================

class Point:
    def __init__(self, x,y):
        self.x = x
        self.y = y

    def __add__(self, other): return Point(self.x+other.x,self.y+other.y)
    def __sub__(self, other): return Point(self.x-other.x,self.y-other.y)
    def __mul__(self, factor): return Point(self.x*factor, self.y*factor)
    def length(self): return (self.y*self.y + self.x*self.x) ** 0.5
    def int_xy(self): return int(self.x+0.5), int(self.y+0.5)
    def left90(self): return Point(-self.y, self.x)


# =========================================================================

class Config:
    """Describe a tiling and its connections, colors, options."""

    # What edge type connects with what?
    # (a tile is represented as a string of up to 8 characters representing the edges)
    compatabilities = {
        '-':'-',
        'A':'a', 'a':'A', 'B':'b', 'b':'B', 'c':'C', 'C':'c', 'd':'D', 'D':'d',
        '1':'1', '2':'2', '3':'3', '4':'4',
        '.':'.'
    }

    # Hexagonal connection pattern:
    #
    #     o o
    #   o * o
    #   o o
    #
    # (all points remain on a square grid, but a regular hexagon pattern
    #  can be formed by a simple linear transformation)

    # [ (y, x, index of reverse connection) ]
    connections_8 = [ (-1, 0, 4), (-1, 1, 5), (0, 1, 6), (1, 1, 7), (1, 0, 0), (1, -1, 1), (0, -1, 2), (-1, -1, 3) ]
    x_mapper_8 = Point(0.5**0.5, 0.5**0.5)
    y_mapper_8 = Point(-0.5**0.5, 0.5**0.5)

    connections_6 = [ (-1, 0, 3), (-1, 1, 4), (0, 1, 5), (1, 0, 0), (1, -1, 1), (0, -1, 2) ]
    x_mapper_6 = Point(1.0, 0.0)
    y_mapper_6 = Point(0.5, 0.75**0.5)

    connections_4 = [ (-1,0,2), (0,1,3), (1,0,0), (0,-1,1) ]
    x_mapper_4 = Point(1.0, 0.0)
    y_mapper_4 = Point(0.0, 1.0)

    default_colors=['8ff', 'f44', 'aaf','449', 'ff0088', 'ff4088', 'ff4040', 'ff00ff', '40c0ff']

    def __init__(self, cfg):
        self.colors = Config.default_colors[:] # Note: make a copy, don't change defaults!
        self.background = 'fff'
        self.foreground = '000'
        self.border = None
        self.fill = None
        self.knot = None
        self.thickness = 1.0
        self.width = 0
        self.height = 0
        self.grid = None
        self.labels = None
        self.forms = []
        self.name = ""

        parse_config(self, cfg)

        if len(self.forms) < 1: raise Exception("Not enough forms, need at least one.")

        self.probabilities = [1] * len(self.forms)

        for i in range(len(self.forms)):
            if "/" in self.forms[i]:
                self.forms[i], self.colors[i%len(self.colors)] = self.forms[i].split("/",1)
            if "*" in self.forms[i]:
                self.forms[i], count = self.forms[i].split("*",1)
                self.probabilities[i] = abs(float(count))

        count = max([len(f) for f in self.forms])
        if count <= 4:
            count = 4
            self.connections = Config.connections_4
            self.x_mapper = Config.x_mapper_4
            self.y_mapper = Config.y_mapper_4
        elif count <= 6:
            count = 6
            self.connections = Config.connections_6
            self.x_mapper = Config.x_mapper_6
            self.y_mapper = Config.y_mapper_6
        elif count <= 8:
            count = 8
            self.connections = Config.connections_8
            self.x_mapper = Config.x_mapper_8
            self.y_mapper = Config.y_mapper_8
        else:
            raise Exception("Too many connections specified in some items (more than 8).")

        for i, item in enumerate(self.forms):
            missings = count - len(item)
            if missings:
                self.forms[i] = item + '-' * missings
            for edge in item:
                if edge not in Config.compatabilities:
                    raise Exception("No compatible connection for form #%d (%s)." % (i+1, item))


# ========================================================================
# Config parser. Convert the text description into a Config.

def parse_common(name_and_synonyms, text):
    """Check if the given text contains an assignment to the given named option, return the value or None."""
    if '=' not in text:
        return None
    for name in name_and_synonyms:
        arg, val = text.split('=')
        if arg.lower() == name:
            return val
    return None

def parse_bool(self, name_and_synonyms, text):
    """Check if the given text contains a boolean assignment to the given named option, return True if successfully parsed."""
    val = parse_common(name_and_synonyms, text)
    if not val:
        return False
    setattr(self, name_and_synonyms[0], bool(int(val)))
    return True

def parse_float(self, name_and_synonyms, text):
    """Check if the given text contains a real number assignment to the given named option, return True if successfully parsed."""
    val = parse_common(name_and_synonyms, text)
    if not val:
        return False
    setattr(self, name_and_synonyms[0], float(val))
    return True

def parse_int(self, name_and_synonyms, text):
    """Check if the given text contains an integer number assignment to the given named option, return True if successfully parsed."""
    val = parse_common(name_and_synonyms, text)
    if not val:
        return False
    setattr(self, name_and_synonyms[0], int(val))
    return True

def parse_text(self, name_and_synonyms, text):
    """Check if the given text contains an assignment to the given named option, return True if successfully parsed."""
    val = parse_common(name_and_synonyms, text)
    if not val:
        return False
    setattr(self, name_and_synonyms[0], val)
    return True

def parse_color(self, name_and_synonyms, text):
    """Check if the given text contains a color assignment to the given named option, return True if successfully parsed."""
    val = parse_common(name_and_synonyms, text)
    if not val:
        return False
    if not all([c in '0123456789abcdefABCDEF' for c in val]):
        raise Exception('Color description "%s" for %s is not in hexadecimal.' %(val, name_and_synonyms[0]))
    setattr(self, name_and_synonyms[0], val)
    return True

def parse_colors(name_and_synonyms, text, sep=','):
    """Convert the given text into separate color text."""
    new_colors = []
    for i, color in enumerate(text.split(sep)):
        if not all([c in '0123456789abcdefABCDEF' for c in color]):
            raise Exception('Color description "%s" for %s is not in hexadecimal.' %(color, name_and_synonyms[0]))
        new_colors.append(color)
    return new_colors

def parse_colors_array(self, name_and_synonyms, text):
    """Check if the given text contains a multiple colors assignment to the given named option, return True if successfully parsed."""
    val = parse_common(name_and_synonyms, text)
    if not val:
        return False
    new_colors = parse_colors(name_and_synonyms, val)
    self.colors[0:len(new_colors)] = new_colors
    return True

def parse_config(self, text):
    """Convert the given text into the known options and ssign them to self. Return the array of text not matching options."""
    parsers = {
        ('knot',)             : parse_bool,
        ('border',)           : parse_bool,
        ('fill',)             : parse_bool,
        ('thickness',)        : parse_float,
        ('width', 'w',)       : parse_int,
        ('height', 'h',)      : parse_int,
        ('background', 'bg',) : parse_color,
        ('foreground', 'fg',) : parse_color,
        ('colors',)           : parse_colors_array,
        ('grid',)             : parse_bool,
        ('labels',)           : parse_bool,
        ('name',)             : parse_text,
    }

    for c in text.split():
        for arg, parser in parsers.items():
            if parser(self, arg, c):
                break
        else:
            self.forms.append(c)


# ========================================================================
# Tiling processing.

class Assembler:
    def __init__(self, connections, compatabilities, forms, probabilities, point_set):
        self.connections = connections    # [(y,x,index of reverse connection)]
        self.compatabilities = compatabilities    # { edge-char -> edge-char }
        self.point_set = point_set   # set of (y,x)

        self.basic_forms = forms   # ['edge types']
        self.forms = [ ]   # ['edge types']
        self.form_id = [ ]   # [original form number]
        self.rotation = [ ]  # [rotation from original]
        self.probabilities = [ ]
        self.tiles = { }   # (y,x) -> form number
        self.dirty = set()   # set of (y,x) -- Possible sites for adding tiles
        self.options_cache = { }   # pattern -> [form_ids]
        self.dead_loci = set([ ]) # [ {(y,x)->form number} ]
        self.history = [ ]
        self.changes = { }

        for id, form in enumerate(forms):
            current = form
            for i in range(len(self.connections)):
                if current not in self.forms:
                    self.forms.append(current)
                    self.form_id.append(id)
                    self.rotation.append(i)
                    self.probabilities.append(probabilities[id])
                current = current[1:] + current[0]

    def update_point_set(self, point_set):
        for pt in point_set:
            if pt not in self.point_set:
                for oy, ox, opposite in self.connections:
                    neighbor = (pt[0] + oy, pt[1] + ox)
                    if neighbor not in point_set:
                        continue
                    if neighbor in self.dirty:
                        continue
                    if neighbor in self.tiles:
                        del self.tiles[neighbor]
                        self.dirty.add(neighbor)
        for pt in list(self.tiles):
            if pt not in point_set:
                del self.tiles[pt]
        self.point_set = point_set

    def put(self, y,x, value):
        if (y,x) in self.changes:
            if value == self.changes[(y,x)]:
                del self.changes[(y,x)]
        else:
            self.changes[(y,x)] = self.tiles.get((y,x),None)

        if value == None:
            if (y,x) not in self.tiles: return
            del self.tiles[(y,x)]
            self.dirty.add((y,x))
        else:
            self.tiles[(y,x)] = value

        for oy, ox, opposite in self.connections:
            y1 = y + oy
            x1 = x + ox
            if (y1,x1) not in self.tiles and (y1, x1) in self.point_set:
                self.dirty.add((y1,x1))

    def get_pattern(self, y,x):
        result = ''
        for oy, ox, opposite in self.connections:
            y1 = y + oy
            x1 = x + ox
            if (y1,x1) in self.tiles:
                result += self.compatabilities[self.forms[self.tiles[(y1,x1)]][opposite]]
            #elif (y1,x1) not in self.point_set:
            #    result += ' '
            else:
                result += '.'

        return result

    def fit_ok(self, pattern,form_number):
        form = self.forms[form_number]
        for i in range(len(self.connections)):
            if pattern[i] != '.' and pattern[i] != form[i]:
                return False

        return True

    def options(self, y,x):
        pattern = self.get_pattern(y,x)
        if pattern in self.options_cache:
            return self.options_cache[pattern]

        result = [ ]
        for i in range(len(self.forms)):
            if self.fit_ok(pattern,i):
                result.append(i)
        result = tuple(result)

        self.options_cache[pattern] = result

        return result

    def locus(self, y,x, rotation=0):
        visited = { }
        neighbours = { }
        todo = [ ((y,x), (0,0)) ]
        result = [ ]

        min_y = 1<<30
        min_x = 1<<30

        while todo:
            current, offset = todo.pop(0)
            if current in visited: continue
            visited[current] = True

            any = False
            new_todo = [ ]
            for i, (oy, ox, opposite) in enumerate(self.connections):
                neighbour = (current[0]+oy, current[1]+ox)
                if neighbour in self.point_set:
                    if neighbour in self.tiles:
                        any = True
                        neighbours[neighbour] = True
                        min_y = min(min_y, offset[0])
                        min_x = min(min_x, offset[1])
                        result.append( (offset, opposite,
                                        self.forms[self.tiles[neighbour]][opposite]) )
                    else:
                        temp = self.connections[(i+rotation) % len(self.connections)]
                        new_offset = (offset[0]+temp[0], offset[1]+temp[1])
                        new_todo.append((neighbour, new_offset))

            if not any and len(self.connections) == 4:
                for oy, ox in ((-1,-1), (-1,1), (1,-1), (1,1)):
                    neighbour = (current[0]+oy, current[1]+ox)
                    if neighbour in self.tiles:
                        any = True
                        break

            if any:
                todo.extend(new_todo)

        result = [ (yy-min_y,xx-min_x,a,b) for ((yy,xx),a,b) in result ]

        return frozenset(result), visited, neighbours


    def filter_options(self, y,x,options):
        result = [ ]
        for i in options:
            self.tiles[(y,x)] = i
            visiteds = [ ]

            for oy, ox, oppoiste in self.connections:
                y1 = y+oy
                x1 = x+ox

                ok = True
                if (y1,x1) not in self.tiles and (y1,x1) in self.point_set:
                    for visited in visiteds:
                        if (y1,x1) in visited:
                            ok = False
                            break
                    if ok:
                        locus, visited, _ = self.locus(y1,x1)
                        visiteds.append(visited)
                        if locus is not None and locus in self.dead_loci:
                            break
            else:
                result.append(i)

            del self.tiles[(y,x)]

        return result

    def any_links_to(self, y,x):
        for oy, ox, opposite in self.connections:
            y1 = y + oy
            x1 = x + ox
            if (y1, x1) in self.tiles:
                if self.forms[self.tiles[(y1,x1)]][opposite] != '-':
                    return True
        return False

    def prune_dead_loci(self):
        for item in list(self.dead_loci):
            if random.randrange(2):
                self.dead_loci.remove(item)

    def iterate(self):
        if not self.tiles:
            self.put(0,0,0)
            self.history.append((0,0))
            return True

        mid_y = 0.0
        mid_x = 0.0
        for y, x in list(self.dirty): # Note: need to convert to list because we modify the set in the loop.
            if (y,x) in self.tiles or not self.any_links_to(y,x):
                self.dirty.remove((y,x))
                continue
            mid_y += y
            mid_x += x

        if not self.dirty:
            return False

        mid_y /= len(self.dirty)
        mid_x /= len(self.dirty)

        point_list = [ ]
        for y, x in self.dirty:
            yy = y - mid_y
            xx = x - mid_x
            sorter = ((yy*2)**2+(xx*2+yy)**2)
            point_list.append( (sorter,y,x) )

        point_list.sort()

        best = None

        for sorter, y, x in point_list:
            options = self.options(y,x)

            if len(options) < 2:
                score = 0
            else:
                score = 1

            if best == None or score < best_score:
                best = options
                best_score = score
                best_x = x
                best_y = y
                if score == 0: break

        if best == None: return False

        best = self.filter_options(best_y,best_x,best)

        if len(best) > 0:
            ws = []
            for i in best:
                ws.append(self.probabilities[i])
            self.put(best_y,best_x,random.choices(best, weights=ws)[0])
            self.history.append((best_y,best_x))
            return True

        #otherwise, backtrack:

        for i in range(len(self.connections)):
            locus, _, relevant = self.locus(best_y,best_x,i)
            if locus is None: break
            self.dead_loci.add(locus)
            if len(locus) > 8: break

        if len(self.dead_loci) > 10000:
            self.prune_dead_loci()

        # Shape of distribution
        autism = 1.0 # 1.0 == normal, >1.0 == autistic (just a theory :-) )

        # Overall level
        adhd = 2.0   # Lower == more adhd

        n = 1
        while n < len(self.tiles)-1 and random.random() < ( n/(n+autism) )**adhd:
            n += 1

        while self.history and (n > 0 or
                                self.locus(best_y,best_x)[0] in self.dead_loci):
            item = self.history.pop(-1)
            self.put(item[0],item[1],None)
            n -= 1

        if not self.tiles:
            return False

        return True


# ========================================================================
# Some maths helpers.

def val2pt(vals):
    return [QtCore.QPoint(int(p[0]),int(p[1])) for p in vals]

def bezier(a,b,c,d):
    result = [ ]
    n = 12
    for i in range(1,n):
        u = float(i) / n
        result.append(
            a * ((1-u)*(1-u)*(1-u)) +
            b * (3*u*(1-u)*(1-u)) +
            c * (3*u*u*(1-u)) +
            d * (u*u*u)
        )
    return result

def normalize(form):
    best = form
    for i in range(len(form)-1):
        form = form[1:] + form[0]
        if form > best: best = form
    return best


# ========================================================================
# UI Helpers


def showException(f):
    """Decorator to keep Python exceptions contained, to avoid crashing Qt."""

    @functools.wraps(f)
    def wrapper(self, *args, **kw):
        try:
            return f(self, *args, **kw)
        except Exception as e:
            QtWidgets.QErrorMessage(self.window).showMessage(str(e))
        except BaseException as e:
            QtWidgets.QErrorMessage(self.window).showMessage(str(e))
            sys.exit(0)

    return wrapper

def eatException(f):
    """Decorator to keep Python exceptions contained, to avoid crashing Qt."""

    @functools.wraps(f)
    def wrapper(self, *args, **kw):
        try:
            return f(self, *args, **kw)
        except:
            pass

    return wrapper

def alloc_color(text):
    """Convert a text description of a color in hexadecimal into a QColor."""
    comp = []
    steps = max(1,len(text)//3)
    for i in range(0,len(text),steps):
        comp.append(int(255 * int(text[i:i+steps], 16) / 16**steps))
    if len(comp) == 1:
        return QtGui.QColor(comp[0], comp[0], comp[0])
    elif len(comp) == 3:
        return QtGui.QColor(comp[0], comp[1], comp[2])
    else:
        return QtGui.QColor(128, 128, 128)

def tweak_color_value(color):
    hue, sat, value, alpha = color.getHsvF()
    if value < 0.5:
        value += 0.05
    else:
        value -= 0.05
    return QtGui.QColor.fromHsvF(hue, sat, value, alpha)

def make_spin(label, min_val, max_val, val, on_changed):
    """Create a spin-box UI to adjust numbers."""
    label = QtWidgets.QLabel(label)
    label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
    if type(min_val) == type(1):
        spin = QtWidgets.QSpinBox()
        spin.setSingleStep(1)
        spin.setRange(min_val, max_val)
        spin.setValue(val)
    else:
        spin = QtWidgets.QDoubleSpinBox()
        spin.setSingleStep(0.1)
        spin.setRange(min_val, max_val)
        spin.setValue(val)
    spin.setObjectName('spin')
    spin.setFrame(True)
    spin.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
    spin.setButtonSymbols(QtWidgets.QSpinBox.NoButtons)
    spin.valueChanged.connect(on_changed)
    spin_more = QtWidgets.QPushButton(' + ')
    spin_more.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
    spin_more.clicked.connect(spin.stepUp)
    spin_more.setObjectName('more')
    spin_less = QtWidgets.QPushButton(' - ')
    spin_less.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
    spin_less.clicked.connect(spin.stepDown)
    spin_less.setObjectName('less')
    frame = make_hbox(0, label, spin_more, spin, spin_less, spacing=0)
    frame.setLineWidth(0)
    frame.setStyleSheet('''
        #more { width: 12px; padding: 3px 4px 5px; }
        #less { width: 12px; padding: 3px 5px 5px; }
        #spin { width: 20px; margin: 1px; }
    ''')
    return spin, frame

def make_check(label, val, on_changed):
    """Create a check-box toggle UI."""
    check = QtWidgets.QCheckBox(label)
    check.setChecked(bool(val))
    check.stateChanged.connect(on_changed)
    return check

def make_box(margins, horiz, *widgets, spacing=None, border=None):
    """Create a container box for other UI elements."""
    if horiz:
        box = QtWidgets.QHBoxLayout()
    else:
        box = QtWidgets.QVBoxLayout()
    box.setContentsMargins(margins, margins, margins, margins)
    if spacing is not None:
        box.setSpacing(spacing)
    frame = QtWidgets.QFrame()
    frame.setLayout(box)
    for w in widgets:
        if type(w) == type(1):
            box.addStretch(w)
        else:
            box.addWidget(w)
    return frame

def make_hbox(margins, *widgets, spacing=None):
    """Create a horizontal container box for other UI elements."""
    return make_box(margins, True, *widgets, spacing=spacing)

def make_vbox(margins, *widgets, spacing=None):
    """Create a vertical container box for other UI elements."""
    return make_box(margins, False, *widgets, spacing=spacing)

def add_click_shortcut(shortcut, widget):
    """Add a keyboard shortcut that simulate a click."""
    sc = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), widget)
    sc.activated.connect(widget.click)

def add_focus_shortcut(shortcut, widget):
    """Add a keyboard shortcut that gives focus to an element."""
    sc = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), widget)
    sc.activated.connect(widget.setFocus)

def add_quit_shortcut(shortcut, widget):
    """Add a keyboard shortcut that closes an element, usually a window."""
    sc = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), widget)
    sc.activated.connect(widget.close)


# ========================================================================
# UI


class Canvas(QtWidgets.QFrame):
    """UI -- a canvas that signals when repaints or resizes are triggered."""

    painting = QtCore.pyqtSignal(['QPainter'])
    resizing = QtCore.pyqtSignal(['QSize'])

    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)
        self.window = self

    @eatException
    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHints(QtGui.QPainter.Antialiasing
                              |QtGui.QPainter.TextAntialiasing
                              |QtGui.QPainter.SmoothPixmapTransform)
        self.painting.emit(painter)
        painter.end()

    @eatException
    def resizeEvent(self, event):
        self.resizing.emit(event.size())

class ConfigOverrideVal:
    """Holds a value which is user-controlled and a optional override value from Config."""

    def __init__(self, val):
        """Starts with only a user value."""
        self.user_val = val
        self.config_val = None

    def __bool__(self):
        """If there is a config value, use that, otherwise use the user value."""
        if self.config_val is None:
            return self.user_val
        else:
            return self.config_val

    def setFromUser(self, val):
        """When set by the user, get rid of the config value; from now on the user has decided."""
        self.config_val = None
        self.user_val = val

    def setFromConfig(self, val):
        """When set from the config, set the config value but leave the user value intact."""
        self.config_val = val


class Interface(QtCore.QObject):
    """Main UI of the program."""

    color_schemes = {
        'No Color Scheme'   : None,
        'Autumn'            : 'f3a800 fc4d41 790005 dd662e ffcb50',
        'Pumpkins'          : 'ff4e00 8ea604 f5bb00 ec9f05 bf3100',
        'Earth Tones'       : '941911 a23718 941b0c bc3908 f6aa1c',
        'Primaries'         : 'ff595e ffca3a 8ac926 1982c4 8a6ca3',
        'Pastel Greens'     : '3ab795 7ad3a8 a0e8af ffcf56 dddac0',
        'Tender Forest'     : '8b4b39 a86544 b5e391 d8f0ad dbd1cb',
        'Teals'             : '98e2c6 51a3a3 b3c3c3 71bbb1 23b5d3',
        'Blues'             : 'b3cbd7 8c9fa7 395161 35a8df b2d8f0',
        'Beach Towel'       : 'e67b03 c7d300 428bca b09e99 eec9c1',
        'Sunrise'           : 'ef798a f7a9a8 ffd289 facc6b fb8131',
        'Sky and Sun'       : '007bb6 04b6f0 ffbc42 d84239 fa7d16',
        'Deco Pool'         : '247ba0 70c1b3 b2dbbf e3efbd e1b694',
        'Bright Toy'        : '5bc0eb dd472c 9bc53d e5e934 fa7921',
        'Grapevine'         : '6d61ab 848bbe 708b75 9ab87a a8d991',
        'Cold to Hot'       : '72b5d3 336fca 64a334 f5b30f cd451b',
        'Warmth Scale'      : 'dad58f e9b45a f4a261 f76f51 f93211',
        'Ocean View'        : '06aed5 086788 f0c808 dfd1c0 edac1a',
        'Make Up'           : 'e8d2cc ffe5d9 ffcad4 f4acb7 9d8189',
        'Oranges'           : '003049 d62828 f77f00 fcbf49 eae2b7',
        'Green Mosaic'      : 'daf3cd c8d5b9 8fc0a9 68b0ab 4a7c59',
        'Fruits'            : '1bb98b 5d60a7 dfe472 ff9b71 e84855',
        'Baby Powder'       : '7bdff2 b2f7ef cfd7d6 f7d6e0 f2b5d4',
        'Ceramics'          : 'b8d8ba d9dbbc fcddbc ef959d 99a8df',
        'River Grass'       : '05668d 427ae9 bbc2da 679436 a5be00',
        'Lapis Lazuli'      : '03358c 2561c2 1768ac 06bee1 05c1d3',
        'Swimming Pool'     : '07beb8 3dccc7 68d8d6 9ceaef c4fff9',
        'Oranges'           : 'cc5803 e2711d ff9505 ffb627 ffc971',
        'Plump'             : '706677 906367 a6808c ccb7ae d6cfcb',
        'Cherries'          : '8f004b a20066 ce4257 ff7f51 ff9b54',
    }

    def __init__(self):
        QtCore.QObject.__init__(self)

        # Data
        self.iteration = 0
        self.width = -1
        self.height = -1
        self.scale = 8
        self.thickness = 1
        self.knot = ConfigOverrideVal(False)
        self.border = ConfigOverrideVal(True)
        self.fill = ConfigOverrideVal(True)
        self.grid = ConfigOverrideVal(True)
        self.labels = ConfigOverrideVal(True)
        self.randomizing = False
        self.iteration = 0
        self.shapes = { }
        self.polys = { }
        self.assembler = None
        self.timer = None
        self.error = None
        self.corner = 0.5
        self.full_paint = True
        self.ignore_from_ui = False # Unfortunate hack to avoid feedback when setting UI.

        # UI
        self.canvas = Canvas()
        self.canvas.painting.connect(self.on_paint)
        self.canvas.resizing.connect(self.on_resize)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        canvas_frame = make_hbox(0, self.canvas)
        canvas_frame.setLineWidth(1)
        canvas_frame.setFrameStyle(Canvas.Box)

        tilings_label = QtWidgets.QLabel('Tilings:')
        tilings_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        tilings_label.setObjectName('tilings_label')
        self.tilings_combo = QtWidgets.QComboBox()
        self.tilings_combo.setMaxVisibleItems(25)
        self.tilings_combo.setEditable(True)
        self.tilings_combo.setInsertPolicy(QtWidgets.QComboBox.InsertAfterCurrent)
        self.tilings_combo.completer().setCaseSensitivity(QtCore.Qt.CaseSensitive)
        for item in catalogue:
            self.tilings_combo.addItem(item)
        self.tilings_combo.currentIndexChanged.connect(self.on_reset)
        self.tilings_combo.setObjectName('tilings_combo')

        random_button = QtWidgets.QPushButton('Random')
        random_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        random_button.clicked.connect(self.on_random)

        tilings_frame = make_hbox(0, tilings_label, self.tilings_combo, random_button)

        save_canvas_button = QtWidgets.QPushButton('Save Canvas')
        save_canvas_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        save_canvas_button.clicked.connect(self.on_save_canvas)

        self.colors_combo = QtWidgets.QComboBox()
        self.colors_combo.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Preferred)
        self.colors_combo.setMaxVisibleItems(40)
        for name in Interface.color_schemes:
            self.colors_combo.addItem(name)
        self.colors_combo.currentIndexChanged.connect(self.on_color_scheme_changed)
        self.colors_combo.setObjectName('colors_combo')

        self.fill_box   = make_check("Filled", self.fill, self.on_fill_changed)
        self.border_box = make_check("Borders", self.border, self.on_border_changed)
        self.knot_box   = make_check("Knot", self.knot, self.on_knot_changed)
        self.grid_box   = make_check("Grid", self.grid, self.on_grid_changed)
        self.labels_box = make_check("Show Tile Labels", self.labels, self.on_labels_changed)

        self.scale_spin,     scale_frame     = make_spin('Size:', 3, 50, self.scale, self.on_set_scale)
        self.corner_spin,    corner_frame    = make_spin('Corner Radius:', 0.1, 0.9, self.corner, self.on_set_corner)
        self.thickness_spin, thickness_frame = make_spin('Thickness:', 1, 8, self.thickness, self.on_set_thickness)

        reset_button = QtWidgets.QPushButton('Restart')
        reset_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        reset_button.clicked.connect(self.on_reset)

        hframe = make_hbox(0,
            3, self.colors_combo, 1, self.fill_box, self.border_box, self.knot_box, self.grid_box, self.labels_box,
            1, reset_button,
            1, scale_frame, thickness_frame, corner_frame, 3, save_canvas_button)

        vframe = make_vbox(4, tilings_frame, hframe, canvas_frame)

        self.window = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(3,3,3,3)
        self.window.setObjectName("window")
        self.window.setLayout(grid)
        self.window.setMinimumSize(600,600)
        self.window.setWindowTitle('Ghost Diagrams')
        grid.addWidget(vframe)

        self.window.setStyleSheet('''
            QLabel#tilings_label { font: 18px; }
            QComboBox#tilings_combo { font: 18px; }
            QPushButton { width: 80px; }
            ''')

        # Shortcuts
        add_click_shortcut('Ctrl+F', self.fill_box)
        add_click_shortcut('Ctrl+B', self.border_box)
        add_click_shortcut('Ctrl+K', self.knot_box)
        add_click_shortcut('Ctrl+G', self.grid_box)
        add_click_shortcut('Ctrl+L', self.labels_box)
        add_click_shortcut('Ctrl+ ', reset_button)
        add_click_shortcut('Ctrl+R', random_button)
        add_click_shortcut('Ctrl+S', save_canvas_button)
        add_focus_shortcut('Ctrl+Z', self.scale_spin)
        add_focus_shortcut('Ctrl+H', self.thickness_spin)
        add_focus_shortcut('Ctrl+O', self.corner_spin)
        add_focus_shortcut('Ctrl+T', self.tilings_combo)
        add_quit_shortcut ('Ctrl+Q', self.window)

        self.reset()

    ###################################################################
    # Event handlers. UI -> Data.

    @showException
    def on_resize(self, sz):
        self.set_size(sz.width(), sz.height())

    @showException
    def on_set_scale(self, value):
        self.scale = value
        self.reset()

    @showException
    def on_set_corner(self, value):
        self.corner = value
        self.shapes = {}
        self.polys = {}
        self.update_full_canvas()

    @showException
    def on_set_thickness(self, value):
        self.thickness = value
        self.update_full_canvas()

    @showException
    def on_color_scheme_changed(self, index):
        self.apply_current_color_scheme()
        self.update_full_canvas()

    def on_something_changed(self, destination, state):
        if self.ignore_from_ui:
            return False
        destination.setFromUser(bool(state))
        self.update_full_canvas()
        return True

    @showException
    def on_fill_changed(self, state):
        self.on_something_changed(self.fill, state)

    @showException
    def on_border_changed(self, state):
        self.on_something_changed(self.border, state)

    @showException
    def on_knot_changed(self, state):
        if self.on_something_changed(self.knot, state):
            self.shapes = {}
            self.polys = {}

    @showException
    def on_labels_changed(self, state):
        if self.on_something_changed(self.labels, state):
            self.update_assembler()

    @showException
    def on_grid_changed(self, state):
        self.on_something_changed(self.grid, state)

    @showException
    def on_reset(self, index = 0):
        self.reset(index)

    @showException
    def on_new_diag(self, text):
        self.reset()

    @showException
    def on_random(self, value):
        self.random()


    @showException
    def on_save_canvas(self, value):
        self.save_canvas()

    @showException
    def on_idle(self):
        """This is where the processing to generate a tiling is done."""
        if not self.assembler.iterate():
            self.timer.stop()
            self.timer = None
            self.update_full_canvas()

        self.iteration += 1

        if self.randomizing and (self.iteration == 100 or not self.timer):
            self.randomizing = False

            forms_present = { }
            for item in self.assembler.tiles.values():
                forms_present[self.assembler.form_id[item]] = 1

            if len(self.assembler.tiles) < 10 \
               or len(forms_present) < len(self.assembler.basic_forms):
                self.random(True)

        if self.iteration % 8 == 0:
            if self.iteration % 1000 == 0:
                self.full_paint = True
            self.canvas.update()

    @showException
    def on_paint(self, painter):
        self.paint_changes(painter)

    ###################################################################
    # Data -> UI.

    def set_config_val(self, val, ui, new_val):
        val.setFromConfig(new_val)
        self.ignore_from_ui = True
        ui.setChecked(bool(val))
        self.ignore_from_ui = False
        self.update_full_canvas()

    def set_grid(self, value):
        self.set_config_val(self.grid, self.grid_box, value)

    def set_knot(self, value):
        self.set_config_val(self.knot, self.knot_box, value)

    def set_labels(self, value):
        self.set_config_val(self.labels, self.labels_box, value)

    def set_border(self, value):
        self.set_config_val(self.border, self.border_box, value)

    def set_fill(self, value):
        self.set_config_val(self.fill, self.fill_box, value)

    def set_scale(self, value):
        if value is None:
            return
        self.scale = value
        self.scale_spin.setValue(self.scale)
        self.reset()

    def set_corner(self, value):
        if value is None:
            return
        self.corner = value
        self.corner_spin.setValue(self.corner)
        self.update_full_canvas()

    def set_thickness(self, value):
        if value is None:
            return
        self.thickness = value
        self.thickness_spin.setValue(self.thickness)
        self.update_full_canvas()

    def set_size(self, new_width, new_height):
        if new_width == self.width and new_height == self.height:
            return
        self.width = new_width
        self.height = new_height
        self.update_assembler()

    def canvas_width(self):
        return max(self.width, self.canvas.width())

    def canvas_height(self):
        return max(self.height, self.canvas.height())

    ###################################################################
    # Starting a new tiling.

    def update_assembler(self):
        if self.assembler:
            self.shapes = { }
            self.polys = { }
            self.assembler.update_point_set(self.create_point_set())
            self.start_idling()
        self.update_full_canvas()

    def create_point_set(self):
        point_set = set()
        yr = int( self.height/self.scale/4 )
        xr = int( self.width/self.scale/4 )
        bound = self.scale * 3
        if self.labels:
            minx = bound
            maxx = self.width  - bound
            miny = bound
            maxy = self.height - bound - 40
        else:
            minx = -bound
            maxx = self.width  + bound
            miny = -bound
            maxy = self.height + bound
        for y in range(-yr,yr):
            for x in range(-xr,xr):
                point = self.pos(x*2, y*2)
                if point.x > minx and point.x < maxx and point.y > miny and point.y < maxy:
                    point_set.add((y,x))
        return point_set

    def reset(self, index = 0):
        try:
            self.config = Config(self.tilings_combo.currentText())
            self.error = None
        except Exception as e:
            self.config = Config("---- grid=0 background=fff foreground=f66")
            self.error = str(e)
            self.update_full_canvas()

        self.set_size(self.config.width  if self.config.width  > 0 else self.canvas.width(),
                      self.config.height if self.config.height > 0 else self.canvas.height())

        self.set_fill(self.config.fill)
        self.set_border(self.config.border)
        self.set_labels(self.config.labels)
        self.set_grid(self.config.grid)
        self.set_knot(self.config.knot)

        self.background = alloc_color(self.config.background)
        self.foreground = alloc_color(self.config.foreground)
        self.colors = [ alloc_color(item) for item in self.config.colors ]

        self.apply_current_color_scheme()

        point_set = self.create_point_set()

        self.randomizing = False
        self.iteration = 0
        self.shapes = { }
        self.polys = { }
        self.full_paint = True
        self.assembler = Assembler(self.config.connections, Config.compatabilities,
                                   self.config.forms, self.config.probabilities, point_set)
        self.start_idling()

    def start_idling(self):
        if not self.timer:
            self.timer = QtCore.QTimer()
            self.timer.timeout.connect(self.on_idle)
            self.timer.start()

    def random(self, same_form=False):
        if same_form:
            n = len(self.assembler.basic_forms)
            sides = len(self.assembler.basic_forms[0])
        else:
            n = random.choice([1,1,2,2,2,3,3,3,4])
            if self.knot:
                sides = 6
            else:
                sides = random.choice([4,6,8])

        while True:
            if self.knot:
                edge_counts = [ random.choice(range(2,sides+1,2))
                                for i in range(n) ]
            else:
                edge_counts = [ random.choice(range(1,sides+1))
                                for i in range(n) ]

            edge_counts.sort()
            edge_counts.reverse()
            if edge_counts[0] != 1: break

        result = [ ]
        def zut(result):
            result.clear()
            previous = '1234' + 'aAbBcCdD' #* 3
            for edge_count in edge_counts:
                item = ['-']*(sides-edge_count)
                for j in range(edge_count):
                    selection = random.choice(previous)
                    previous += Config.compatabilities[selection]*6 #12
                    item.append(selection)

                random.shuffle(item)
                item = normalize(''.join(item))
                if item in result: return True
                result.append(item)

            all = ''.join(result)
            for a, b in Config.compatabilities.items():
                if a in all and b not in all: return True
            return False
        while zut(result):
            pass

        self.tilings_combo.addItem(' '.join(result))
        self.tilings_combo.setCurrentIndex(self.tilings_combo.count()-1)
        self.reset()
        self.randomizing = True

    ###################################################################
    # Painting and rendering.

    def update_full_canvas(self):
        """Force a full repaint of the canvas."""
        self.full_paint = True
        self.canvas.update()

    def apply_current_color_scheme(self):
        self.set_color_scheme(self.colors_combo.currentText())

    def set_color_scheme(self, scheme):
        if scheme not in Interface.color_schemes:
            return
        colors = Interface.color_schemes[scheme]
        if not colors:
            if self.config:
                self.colors = [ alloc_color(item) for item in self.config.colors ]
            return
        new_colors = parse_colors(scheme, colors, ' ')
        new_colors = [alloc_color(c) for c in new_colors]
        self.colors[0:len(new_colors)] = new_colors

    def pos(self, x,y, center=True):
        result = (self.config.x_mapper*x + self.config.y_mapper*y) * (self.scale*2)
        if center:
            return result + Point(self.width/2.0,self.height/2.0)
        else:
            return result

    def make_shape(self, form_number):
        if form_number in self.shapes:
            return self.shapes[form_number]

        result = [ ]
        connections = { }

        octogonal = (len(self.assembler.connections) == 8)

        for i in range(len(self.assembler.connections)):
            yy, xx = self.assembler.connections[i][:2]
            symbol = self.assembler.forms[form_number][i]
            if symbol in '.-': continue

            edge = self.pos(xx, yy, False)
            out = edge
            left = out.left90()

            if symbol in 'aA1':
                r = 0.4
                #r = 0.6
            elif symbol in 'bB2':
                r = 0.3
            elif symbol in 'cC3':
                r = 0.225
            else:
                r = 0.15

            if octogonal:
                r *= 0.7

            if symbol in 'ABCD':
                poke = 0.3 #r
            elif symbol in 'abcd':
                poke = -0.3 #-r
            else:
                poke = 0.0

            points = [
                edge + left*-r,
                edge + out*poke,
                edge + left*r,
            ]

            result.append( (out * (1.0/out.length()), points, self.corner))
            connections[i] = points

        if len(result) == 1:
            point = result[0][0]*(self.scale*-0.7)
            result.append( (result[0][0].left90()*-1.0, [point], 0.8) )
            result.append( (result[0][0].left90(), [point], 0.8) )

        poly = [ ]
        for i in range(len(result)):
            a = result[i-1][1][-1]
            d = result[i][1][0]
            length = (d-a).length() * ((result[i][2]+result[i-1][2])*0.5)
            b = a - result[i-1][0]*length
            c = d - result[i][0]*length
            poly.extend(bezier(a,b,c,d))
            poly.extend(result[i][1])

        links = [ ]
        if self.knot:
            form = self.assembler.forms[form_number]
            items = list(connections.keys())
            cords = [ ]

            if len(items)%2 != 0:
                for item in items[:]:
                    if (item+len(form)/2)   % len(form) not in items and \
                       (item+len(form)/2+1) % len(form) not in items and \
                       (item+len(form)/2-1) % len(form) not in items:
                        items.remove(item)

            if len(items)%2 != 0:
                for i in range(len(form)):
                    if form[i] not in '.-' and \
                       form.count(form[i]) == 1 and \
                       (Config.compatabilities[form[i]] == form[i] or \
                        form.count(Config.compatabilities[form[i]])%2 == 0):
                        items.remove(i)

            if len(items)%2 != 0:
                for item in items[:]:
                    if (item+len(form)//2) % len(form) not in items:
                        items.remove(item)

            if len(items)%2 == 0:
                rot = self.assembler.rotation[form_number]
                mod = len(self.assembler.connections)
                items.sort(key=functools.cmp_to_key(lambda a,b: (a+rot)%mod - (b+rot)%mod))
                step = len(items)//2

                for ii in range(len(items)//2):
                    i = items[ii]
                    j = items[ii-step]
                    cords.append((i,j))

            for i,j in cords:
                a = connections[i]
                b = connections[j]
                a_in = (a[-1]-a[0]).left90()
                a_in = a_in*(self.scale*1.25/a_in.length())
                b_in = (b[-1]-b[0]).left90()
                b_in = b_in*(self.scale*1.25/b_in.length())
                a = [(a[0]+a[1])*0.5,a[1],(a[-2]+a[-1])*0.5]
                b = [(b[0]+b[1])*0.5,b[1],(b[-2]+b[-1])*0.5]
                bez1 = bezier(a[-1],a[-1]+a_in,b[0]+b_in,b[0])
                bez2 = bezier(b[-1],b[-1]+b_in,a[0]+a_in,a[0])
                linker = a + bez1 + b + bez2
                links.append((linker,a[-1:]+bez1+b[:1],b[-1:]+bez2+a[:1]))

        self.shapes[form_number] = poly, links
        return poly, links

    def setPaintColors(self, painter, edge, fill):
        if edge:
            pen = QtGui.QPen(edge)
            pen.setWidth(max(1,int(self.thickness * self.config.thickness)))
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setPen(pen)
        else:
            painter.setPen(QtGui.QPen(QtCore.Qt.NoPen))
        if fill:
            painter.setBrush(QtGui.QBrush(fill))
        else:
            painter.setBrush(QtGui.QBrush(QtCore.Qt.NoBrush))

    def setPaintFont(self, painter, size):
        font = painter.font()
        font.setPixelSize(size)
        painter.setFont(font)

    def get_color(self, i):
        return self.colors[i % len(self.colors)]

    def draw_poly(self, y,x,form_number, painter, erase=False):
        id = (y,x,form_number)

        if id not in self.polys:
            def intify(points): return [ ((middle+point)).int_xy() for point in points ]

            middle = self.pos(x*2,y*2)

            poly, links = self.make_shape(form_number)
            poly = intify(poly)
            links = [ (intify(link), intify(line1), intify(line2)) for link,line1,line2 in links ]

            self.polys[id] = poly, links
        else:
            poly, links = self.polys[id]

        if len(poly) > 0:
            if erase:
                color = self.background
                self.setPaintColors(painter, color, color)
            else:
                color = self.get_color(self.assembler.form_id[form_number])

            if self.fill:
                if not erase:
                    self.setPaintColors(painter, None, color)
                painter.drawPolygon(*val2pt(poly))

            if self.knot:
                for link, line1, line2 in links:
                    if not erase:
                        self.setPaintColors(painter, None, self.foreground)
                    painter.drawPolygon(*val2pt(link))
                    if not erase:
                        if self.fill:
                            self.setPaintColors(painter, color, None)
                        else:
                            self.setPaintColors(painter, self.background, None)
                    #painter.drawPolygon(*val2pt(link))
                    painter.drawPolyline(*val2pt(line1))
                    painter.drawPolyline(*val2pt(line2))

            if self.border:
                if not erase:
                    self.setPaintColors(painter, self.foreground, None)
                painter.drawPolygon(*val2pt(poly))

    def draw_text(self, painter, x, y, padding, with_rect, text):
        alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextWordWrap
        r = painter.boundingRect(x, y, self.canvas_width() - x, self.canvas_height() - y, alignment, text)
        r.adjust(-padding, -padding, padding * 2, padding * 2)
        if with_rect:
            painter.drawRect(r)
        alignment = QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap
        painter.drawText(r, alignment, text)
        return r.right() + padding * 2

    def save_canvas(self):
        fn, image_format = QtWidgets.QFileDialog.getSaveFileName(self.window, "Select Destination Image", "", "Images (*.png *.jpg)")
        self.save_canvas_into(fn)

    def save_canvas_into(self, fn):
        if not fn:
            return
        image = QtGui.QImage(self.width, self.height, QtGui.QImage.Format_RGB32)
        painter = QtGui.QPainter(image)
        painter.setRenderHints(QtGui.QPainter.Antialiasing
                              |QtGui.QPainter.TextAntialiasing
                              |QtGui.QPainter.SmoothPixmapTransform)
        self.repaint_all(painter)
        painter.end()
        image.save(fn)

    def paint_labels(self, painter):
        fontSize = 16
        padding = 6
        self.setPaintFont(painter, fontSize)
        x = padding * 2
        y = self.canvas_height() - fontSize - padding * 4
        if self.config.name:
            self.setPaintColors(painter, self.foreground, self.background)
            x = self.draw_text(painter, x, y, padding, False, self.config.name)
        counts = collections.defaultdict(int)
        for i in self.assembler.tiles.values():
            counts[self.assembler.form_id[i]] += 1
        for i, form in enumerate(self.assembler.basic_forms):
            self.setPaintColors(painter, self.foreground, self.get_color(i))
            x = self.draw_text(painter, x, y, padding, True, '%s x %d' % (form, counts[i]))

    def paint_grid(self, painter):
        self.setPaintColors(painter, tweak_color_value(self.background), None)
        f = 4.0 / len(self.config.connections)
        for (y,x) in self.assembler.point_set:
            poly = [ ]
            for i in range(len(self.config.connections)):
                a = self.config.connections[i-1]
                b = self.config.connections[i]
                poly.append((self.pos(x*2+(a[0]+b[0])*f,y*2+(a[1]+b[1])*f)).int_xy())

            painter.drawPolygon(*val2pt(poly))

    def paint_tiles(self, painter):
        # Note: we do the drawing in two passes to that octogonal tilings overlap more gracefully.
        for (y,x), form_number in self.assembler.tiles.items():
            if y % 2 == x % 2:
                self.draw_poly(y,x,form_number,painter)
        for (y,x), form_number in self.assembler.tiles.items():
            if y % 2 != x % 2:
                self.draw_poly(y,x,form_number,painter)

    def paint_error(self, painter):
        self.setPaintColors(painter, QtGui.QColor(0,0,0), QtGui.QColor(240,200,200))
        painter.drawRect(0, 0, self.canvas.width(), self.canvas.height())
        self.setPaintFont(painter, 24)
        painter.drawText(0, 0, self.canvas.width(), self.canvas.height(), QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, self.error)

    def repaint_all(self, painter):
        self.full_paint = False
        self.setPaintColors(painter, None, self.background)
        painter.drawRect(0, 0, self.canvas_width(), self.canvas_height())

        if self.labels:
            self.paint_labels(painter)

        if self.grid:
            self.paint_grid(painter)

        self.paint_tiles(painter)

        if self.error:
            self.paint_error(painter)

    def paint_changes(self, painter):
        if self.full_paint:
            self.repaint_all(painter)

        changes = self.assembler.changes
        self.assembler.changes = { }
        for y,x in changes:
            old = changes[(y,x)]
            if old is not None:
                self.draw_poly(y,x,old, painter, True)
        for y,x in changes:
            new = self.assembler.tiles.get((y,x),None)
            if new is not None:
                self.draw_poly(y,x,new, painter, False)


# ========================================================================
# Entry.


def seeders(n, seeds, max_connections):
    seed = seeds[0]
    other_seeds = seeds[1:]
    base = len(seed)
    done = { }
    for i in range(1, base ** n):
        grown = ""
        for j in range(n):
            grown += seed[(i // (base ** j)) % base]
        if len(grown) - grown.count('-') > max_connections:
            continue
        grown = normalize(grown)
        if grown in done or grown.swapcase() in done:
            continue
        if other_seeds:
            for other_grown in seeders(n, other_seeds, max_connections):
                result = tuple(sorted((grown,) + other_grown))
                swap_result = (t.swapcase() for t in result)
                if result in done or swap_result in done:
                    continue
                done[result] = True
                yield result
        else:
            yield (grown,)

def parse_command_line():
    parser = optparse.OptionParser()
    parser.add_option('-q', '--quiet', action='store_true', dest='quiet', default=False, help='be more quiet')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False, help='be more verbose')
    parser.add_option('--no-ui', action='store_true', dest='no_ui', default=False, help='do not open the user interface')
    parser.add_option('--max-iter', action='store', type='int', dest='max_iterations', default=10000, help='maximum number of iteration to fill the grid before giving up')
    parser.add_option('--min-tiles', action='store', type='int', dest='min_tiles', default=10, help='minimum number of tiles on the grid to save the result')
    parser.add_option('-c', '--max-connections', action='store', type='int', dest='max_connections', default=1000, help='maximum number of valid connections per tile type')
    parser.add_option('-g', '--grid', action='store', type='int', dest='grid', default=4, help='number of sides of the tiles (4, 6 or 8)')
    parser.add_option('--width', action='store', type='int', dest='width', default=600, help='width of the image to generate and save')
    parser.add_option('--height', action='store', type='int', dest='height', default=600, help='height of the image to generate and save')
    return parser.parse_args()

if __name__ == '__main__':

    opts, args = parse_command_line()

    app = QtWidgets.QApplication(sys.argv)
    ui = Interface()

    if not args:
        ui.window.show()
        app.exec()
        sys.exit(0)

    # Just some phd stuff...

    if not opts.no_ui:
        ui.window.show()

    for i, tiles in enumerate(seeders(opts.grid, args, opts.max_connections)):
        diagram = ' '.join(tiles)


        if opts.verbose:
            print(diagram, end='')
        elif not opts.quiet:
            print('%s (%d)' % (diagram, i), end='\r')

        ui.tilings_combo.setCurrentText("%s w=%d h=%d" % (diagram, opts.width, opts.height))
        ui.reset()

        iterations = opts.max_iterations
        while ui.timer and iterations > 0:
            app.processEvents()
            iterations -= 1

        if ui.assembler.dirty:
            if opts.verbose:
                print(" --- failed")
            continue

        if len(ui.assembler.tiles) < opts.min_tiles:
            if opts.verbose:
                print(" --- too simple")
            continue

        if opts.verbose:
            print("")

        ui.save_canvas_into("T" + diagram.replace(" ","+") + ".png")

