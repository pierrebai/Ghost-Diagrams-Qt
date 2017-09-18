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

     A tile set specification is a list of 6- or 4-character strings,
     eg B-Aa-- b--Aa-

     Each character represents a tile edge. Letters (abcd, ABCD)
     match with their opposite case. Numbers match with themselves.

     A tile specifiction can be multiplied by a number to make it
     that much likely to be selected.

     A number of extra paramters can also be supplied:

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

     eg B-Aa-- b--Aa- width=1000 height=1000 thickness=0.5 colors=[000,000,fff,f00]

  Change log:

     0.1 -- initial release
     0.2 -- don't segfault on empty tiles
     0.3 -- random keeps trying till it finds something that will grow
            optimization (options_cache)
     0.4 -- assembly algorithm tweaks
            random tile set tweaks
     0.5 -- Patch by Jeff Epler
             - allow window resizing
             - new connection types (33,44,cC,dD)
             - DNA tile set
            widget to set size of tiles
            no repeated tiles in random
            improvements to assembler
     0.6 -- Use Bezier curves
            Parameters to set width, height, thickness, color
            Save images
     0.7 -- Allow square tiles
            Smarter assembler
            Animate assembly
     0.8 -- Knotwork
            Don't fill all of memory
            Use psyco if available
     0.9 -- Better parsing, simplified fornat, better error report,
            support labels, use Qt instead of gtk,
            support variable probabilities.

  TODO: don't backtrack areas outside current locus
        (difficulty: accidentally creating disconnected islands)

  TODO: (blue sky) 3D, third dimension == time
"""

try:
    import psyco
    psyco.profile()
except:
    pass

__version__ = '0.9'

import sys, os, random, math, functools
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets


# ========================================================================
# Some maths helpers.

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
# Some cool tile sets people have found

catalogue = [
    "dD4- 4-4- 4a4A aA-- a-A-",
    "a4-4A- 4-4--- aA---- a--A-- 4Dd--- name=Arteries",
    "31--1- 111--- 11----",
    "dDc3 c-3- C--3 3---",
    "Bbb- B--- BBb- name=Carvings",
    "A222 222- a--1",
    "aAa3 A--3 a--3 3---",
    "b-22 B--2 b---",
    "11111- 1-----",
    "222221 222---",
    "222221 222223 name=two-zones",
    "aaaa11 a----- 1----- A----- A--A--*10 A--a--*3",
    "4444 c4-4 C--4 4---",
    "42-2 22-- 2-2-",
    "3333-- 333-3- 33----",
    "33333- 33----",
    "33333- 3-3---",
    "444444 4-4--3 4-3--3 44--4-",
    "c414*5 4444*5 C4--*5 4---",
    "1111-- 1-1---",
    "c44444 444444 4C44-- c--4--/f C--4--/f border=0",
    "cC-cC-*3 c-c-4-*3 C----- name=SSSS",
    "cC-cC-*3/f c-c-4-*3/f C-----/f name=SSSS background=0 grid=0 foreground=d labels=0",
    "C332 c33- C-33 name=Alternance",
    "ddDD dDdD dD--",
    "3333-- name=triangles labels=1",
    "3322-- 2--2--*10 name=two-sizes labels=1",
    "cABa aCAb aA-- aCA- acA- name=trains",
    "--33Aa -33-Aa",
    "--33Aa/000 -33-Aa/000 background=fff foreground=888 border=0 grid=0",
    "ab-A-- B--C-- B--c-- B--D-- B--d--",
    "d-D-4- d--D-- 44----",
    "AaAa--",
    "aA---- AaAa--",
    "---bB- bAaB-- aAaA--",
    "B-Aa-- b--Aa-",
    "44---- 11--4-",
    "3-3-3- 33----",
    "1-1-1- 2--12-",
    "-a---- a-AA--",
    "-AAaa- a--A--",
    "-a-A-- Aaa--A",
    "a--a-- -aAA-A",
    "-a-A-a ----A-",
    "--AA-A a-a-a-",
    "a--aa- ----AA",
    "A-A-a- a-a---",
    "A-A-a- a--a--",
    "-a---4 a4-44A 4A----",
    "a2--A- -a2-A2",
    "a-2a2- -A---A -----2",
    "141--- 4--4-- 1-1---",
    "-22-22 22----",
    "-Aaa-- A1A--- a-1AAa",
    "aA-a2- 2A---- --2--A",
    "--bB1- -b--B-",
    "BbB-1- -----b",
    "b--b-b --BbB-",
    "aA1--- ---AA- a--2--",
    "-a--4- -4-4-- --A441",
    "212111 -1-2--",
    "22222a 22-A22",
    "2-222- 2---B2 --b--2",
    "-21221 ---221 ---2-2",
    "-a-a-a ---A-A",
    "-Dd-cA ---d-D ---a-C",
    "--CCCc -3Ca-A --3--c -----c",
    "-C-dDc --CC-C ---ccC",
    "-Aa-Cc -----c -----C",
    "-CcDdC --cC-c -----C",
    "--CcCc -CcC-c ---c-C",
    "A-1-1- a1---B b--1--",
    "aa-aa-/fff AA----/fff A--A--/fff grid=0 border=0 thickness=0.3",
    "bb-bb- BB---- B--B--",
    "-44B4D -dbB4b -44D-d ----44",
    "--d3-3 ---D-D",
    "--cc-c -C-C-c",
    "AaAaaa --1-Aa -----A",
    "d-D-3- dD---- 3-----",
    "a-1-A- a--A--",
    "cCCcCC cccC-- c-C--C",
    "A44444 a4---4 4-4---",
    "acaACA acbBCB bcaBCB bcbACA",
    "A--ab- B-ab-- A--a-- B--b-- ABd--D name=Tree",
    "d-AD-- -a--A- a---A- aa-A--", # Counter-(?),
    "bBbBBB bb---- b---B-",
    "a-AA-A a-a---",
    "cC-a-A a-A---",
    "bbB--B b-BBB- bb----",
    "cCc-C- cC-c-C",
    "d4-Dd- d-D--- DD----",
    "-111",
    "abA- B-C- B-c- B-D- B-d-",
    "4A4a --a4 -A-B --Ab",
    "acAC adBD bcBD bdAC",
    "1111 ---1",
    "-bbb --BB",
    "1B1B a-A- -bA- ab-B",
]


# =========================================================================

class Config:
    """Describe a tiling adn its connections, colors, options."""

    # What edge type connects with what?
    # (a tile is represented as a string of 6 characters representing the 6 edges)
    compatabilities = {
        '-':'-',
        'A':'a', 'a':'A', 'B':'b', 'b':'B', 'c':'C', 'C':'c', 'd':'D', 'D':'d',
        '1':'1', '2':'2', '3':'3', '4':'4'
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
        self.thickness = 1.0
        self.width = -1
        self.height = -1
        self.grid = None
        self.labels = None
        self.forms = []
        self.name = ""

        parse_config(self, cfg)

        self.colors += Config.default_colors[len(self.colors):]

        if len(self.forms) < 1: raise Exception("Not enough forms, need at least one.")

        self.probabilities = [1] * len(self.forms)

        for i in range(len(self.forms)):
            if "/" in self.forms[i]:
                self.forms[i], self.colors[i%len(self.colors)] = self.forms[i].split("/",1)
            if "*" in self.forms[i]:
                self.forms[i], count = self.forms[i].split("*",1)
                self.probabilities[i] = int(count)

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
        else:
            raise Exception("Too many connections specified in some items (more than 6).")

        for i, item in enumerate(self.forms):
            missings = count - len(item)
            if missings:
                self.forms[i] = item + '-' * missings
            for edge in item:
                if edge not in Config.compatabilities:
                    raise Exception("No compatible connection for form #%d (%s)." % (i+1, item))


# ========================================================================
# Config parser. Convert the text description into a Config.

def alloc_color(text):
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

def parse_common(name, text):
    if '=' not in text:
        return None
    if name not in text:
        return None
    arg, val = text.split('=')
    if arg.lower() != name:
        return None
    return val

def parse_bool(self, name, text):
    val = parse_common(name, text)
    if not val:
        return False
    setattr(self, name, bool(int(val)))
    return True

def parse_float(self, name, text):
    val = parse_common(name, text)
    if not val:
        return False
    setattr(self, name, float(val))
    return True

def parse_int(self, name, text):
    val = parse_common(name, text)
    if not val:
        return False
    setattr(self, name, int(val))
    return True

def parse_text(self, name, text):
    val = parse_common(name, text)
    if not val:
        return False
    setattr(self, name, val)
    return True

def parse_color(self, name, text):
    val = parse_common(name, text)
    if not val:
        return False
    if not all([c in '0123456789abcdefABCDEF' for c in val]):
        raise Exception('Color description "%s" for %s is not in hexadecimal.' %(val, name))
    setattr(self, name, val)
    return True

def parse_colors_array(self, name, text):
    val = parse_common(name, text)
    if not val:
        return False
    for i, color in enumerate(val.split(',')):
        if not all([c in '0123456789abcdefABCDEF' for c in color]):
            raise Exception('Color description "%s" for %s is not in hexadecimal.' %(color, name))
        self.colors[i] = color
    return True

def parse_config(self, text):
    parsers = {
        'border'        : parse_bool,
        'fill'          : parse_bool,
        'thickness'     : parse_float,
        'width'         : parse_int,
        'height'        : parse_int,
        'background'    : parse_color,
        'foreground'    : parse_color,
        'colors'        : parse_colors_array,
        'grid'          : parse_bool,
        'labels'        : parse_bool,
        'name'          : parse_text,
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
        self.point_set = point_set   # (y,x) -> True

        self.basic_forms = forms   # ['edge types']
        self.forms = [ ]   # ['edge types']
        self.form_id = [ ]   # [original form number]
        self.rotation = [ ]  # [rotation from original]
        self.probabilities = [ ]
        self.tiles = { }   # (y,x) -> form number
        self.dirty = { }   # (y,x) -> True   -- Possible sites for adding tiles
        self.options_cache = { }   # pattern -> [form_ids]
        self.dead_loci = set([ ]) # [ {(y,x)->form number} ]
        self.history = [ ]
        self.total_y = 0
        self.total_x = 0
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

    def put(self, y,x, value):
        if (y,x) in self.changes:
            if value == self.changes[(y,x)]:
                del self.changes[(y,x)]
        else:
            self.changes[(y,x)] = self.tiles.get((y,x),None)


        if (y,x) in self.tiles:
            self.total_y -= y
            self.total_x -= x

        if value == None:
            if (y,x) not in self.tiles: return
            del self.tiles[(y,x)]
            self.dirty[(y,x)] = True
        else:
            self.tiles[(y,x)] = value
            self.total_y += y
            self.total_x += x

        for oy, ox, opposite in self.connections:
            y1 = y + oy
            x1 = x + ox
            if (y1,x1) not in self.tiles and (y1, x1) in self.point_set:
                self.dirty[(y1,x1)] = True

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
            result = self.options_cache[pattern]

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
        for y, x in list(self.dirty.keys()):
            if (y,x) in self.tiles or not self.any_links_to(y,x):
                del self.dirty[(y,x)]
                continue
            mid_y += y
            mid_x += x

        if not self.dirty:
            return False

        mid_y /= len(self.dirty)
        mid_x /= len(self.dirty)

        point_list = [ ]
        for y, x in self.dirty.keys():
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
# UI


def showException(f):
    """Letting Python exception through to Qt crashes Python, so keep them contained."""

    @functools.wraps(f)
    def wrapper(self, *args, **kw):
        try:
            return f(self, *args, **kw)
        except Exception as e:
            QtWidgets.QErrorMessage(self.window).showMessage(str(e))

    return wrapper


class Canvas(QtWidgets.QFrame):
    """UI -- a canvas that signals when repaints or resizes are triggered."""

    painting = QtCore.pyqtSignal(['QPainter'])
    resizing = QtCore.pyqtSignal(['QSize'])

    def __init__(self):
        QtWidgets.QFrame.__init__(self)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        self.painting.emit(painter)
        painter.end()

    def resizeEvent(self, event):
        self.resizing.emit(event.size())


class Interface(QtCore.QObject):
    """Main UI of the program."""

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.iteration = 0
        self.width = 1000
        self.height = 800
        self.scale = 8
        self.thickness = 1
        self.knot = False
        self.border = True
        self.fill = True
        self.grid = True
        self.randomizing = False
        self.iteration = 0
        self.shapes = { }
        self.polys = { }
        self.assembler = None
        self.timer = None
        self.error = None
        self.labels = True
        self.corner = 0.5
        self.full_paint = True

        self.canvas = Canvas()
        self.canvas.painting.connect(self.on_paint)
        self.canvas.resizing.connect(self.on_size)
        self.canvas.resize(self.width, self.height)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.setLineWidth(1)
        self.canvas.setFrameStyle(Canvas.Box)

        tilings_label = QtWidgets.QLabel('Tilings:')
        tilings_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        tilings_label.setObjectName('tilings_label')
        self.tilings_combo = QtWidgets.QComboBox()
        self.tilings_combo.setEditable(True)
        self.tilings_combo.completer().setCaseSensitivity(QtCore.Qt.CaseSensitive)
        for item in catalogue:
            self.tilings_combo.addItem(item)
        self.tilings_combo.currentIndexChanged.connect(self.on_reset)
        self.tilings_combo.setObjectName('tilings_combo')

        random_button = QtWidgets.QPushButton('Random')
        random_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        random_button.clicked.connect(self.on_random)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(0,0,0,0)
        tilings_frame = QtWidgets.QFrame()
        tilings_frame.setLayout(hbox)
        hbox.addWidget(tilings_label)
        hbox.addWidget(self.tilings_combo)
        hbox.addWidget(random_button)

        self.fill_box = QtWidgets.QCheckBox("Filled")
        self.fill_box.setChecked(self.fill)
        self.fill_box.stateChanged.connect(self.on_fill_changed)

        self.border_box = QtWidgets.QCheckBox("Borders")
        self.border_box.setChecked(self.border)
        self.border_box.stateChanged.connect(self.on_border_changed)

        self.knot_box = QtWidgets.QCheckBox("Knot")
        self.knot_box.setChecked(self.knot)
        self.knot_box.stateChanged.connect(self.on_knot_changed)

        self.grid_box = QtWidgets.QCheckBox("Grid")
        self.grid_box.setChecked(self.grid)
        self.grid_box.stateChanged.connect(self.on_grid_changed)


        self.labels_box = QtWidgets.QCheckBox("Show Tile Labels")
        self.labels_box.setChecked(self.labels)
        self.labels_box.stateChanged.connect(self.on_labels_changed)

        scale_label = QtWidgets.QLabel('Size:')
        scale_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.scale_spin = QtWidgets.QSpinBox()
        self.scale_spin.setSingleStep(1)
        self.scale_spin.setRange(3, 50)
        self.scale_spin.setValue(self.scale)
        self.scale_spin.valueChanged.connect(self.on_set_scale)

        corner_label = QtWidgets.QLabel('Corner Radius:')
        corner_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.corner_spin = QtWidgets.QDoubleSpinBox()
        self.corner_spin.setRange(0.1, 0.9)
        self.corner_spin.setSingleStep(0.1)
        self.corner_spin.setValue(self.corner)
        self.corner_spin.valueChanged.connect(self.on_set_corner)

        thickness_label = QtWidgets.QLabel('Thickness:')
        thickness_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        self.thickness_spin = QtWidgets.QSpinBox()
        self.thickness_spin.setSingleStep(1)
        self.thickness_spin.setRange(1, 8)
        self.thickness_spin.setValue(self.thickness)
        self.thickness_spin.valueChanged.connect(self.on_set_thickness)

        reset_button = QtWidgets.QPushButton('Restart')
        reset_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        reset_button.clicked.connect(self.on_reset)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(2,2,2,2)
        hframe = QtWidgets.QFrame()
        hframe.setLayout(hbox)
        hbox.addStretch(3)
        hbox.addWidget(self.fill_box)
        hbox.addWidget(self.border_box)
        hbox.addWidget(self.knot_box)
        hbox.addWidget(self.grid_box)
        hbox.addWidget(self.labels_box)
        hbox.addStretch(1)
        hbox.addWidget(reset_button)
        hbox.addStretch(1)
        hbox.addWidget(scale_label)
        hbox.addWidget(self.scale_spin)
        hbox.addWidget(thickness_label)
        hbox.addWidget(self.thickness_spin)
        hbox.addWidget(corner_label)
        hbox.addWidget(self.corner_spin)
        hbox.addStretch(3)

        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(4,4,4,4)
        vframe = QtWidgets.QFrame()
        vframe.setLayout(vbox)
        vbox.addWidget(tilings_frame)
        vbox.addWidget(hframe)
        vbox.addWidget(self.canvas)

        self.window = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout()
        grid.setContentsMargins(3,3,3,3)
        self.window.setObjectName("window")
        self.window.setLayout(grid)
        self.window.setMinimumSize(600,600)
        self.window.setWindowTitle('Ghost Diagrams')
        grid.addWidget(vframe)

        self.window.setStyleSheet(
            '''
            QLabel#tilings_label { font: 18px; }
            QComboBox#tilings_combo { font: 18px; }
            QSpinBox, QDoubleSpinBox {
                width: 60px;
            }
            '''
        )

        def add_click_shortcut(shortcut, widget):
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), widget)
            sc.activated.connect(widget.click)

        def add_focus_shortcut(shortcut, widget):
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), widget)
            sc.activated.connect(widget.setFocus)

        def add_quit_shortcut(shortcut, widget):
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(shortcut), widget)
            sc.activated.connect(widget.close)

        add_click_shortcut('Ctrl+F', self.fill_box)
        add_click_shortcut('Ctrl+B', self.border_box)
        add_click_shortcut('Ctrl+K', self.knot_box)
        add_click_shortcut('Ctrl+G', self.grid_box)
        add_click_shortcut('Ctrl+L', self.labels_box)
        add_click_shortcut('Ctrl+ ', reset_button)
        add_click_shortcut('Ctrl+R', random_button)
        add_focus_shortcut('Ctrl+S', self.scale_spin)
        add_focus_shortcut('Ctrl+H', self.thickness_spin)
        add_focus_shortcut('Ctrl+C', self.corner_spin)
        add_focus_shortcut('Ctrl+T', self.tilings_combo)

        add_quit_shortcut('Ctrl+Q', self.window)

        self.reset()

    ###################################################################
    # Event handlers. UI -> Data.

    @showException
    def on_size(self, sz):
        self.width = sz.width()
        self.height = sz.height()
        self.reset()

    @showException
    def on_set_scale(self, value):
        self.scale = value
        self.reset()

    @showException
    def on_set_corner(self, value):
        self.corner = value
        self.shapes = {}
        self.polys = {}
        self.full_paint = True
        self.canvas.update()

    @showException
    def on_set_thickness(self, value):
        self.thickness = value
        self.full_paint = True
        self.canvas.update()

    @showException
    def on_fill_changed(self, state):
        self.fill = state
        self.full_paint = True
        self.canvas.update()

    @showException
    def on_border_changed(self, state):
        self.border = state
        self.full_paint = True
        self.canvas.update()

    @showException
    def on_knot_changed(self, state):
        self.knot = state
        self.shapes = {}
        self.polys = {}
        self.full_paint = True
        self.canvas.update()

    @showException
    def on_labels_changed(self, state):
        self.labels = state
        self.full_paint = True
        self.canvas.update()

    @showException
    def on_grid_changed(self, state):
        self.grid = state
        self.full_paint = True
        self.canvas.update()

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
    def on_idle(self):
        if not self.assembler.iterate():
            self.timer.stop()
            self.timer = None
            self.full_paint = True
            self.canvas.update()

        self.iteration += 1

        if self.randomizing and self.iteration == 100:
            self.randomizing = False

            forms_present = { }
            for item in self.assembler.tiles.values():
                forms_present[self.assembler.form_id[item]] = 1

            #if len(self.assembler.tiles) < 10 \
            #   or len(forms_present) < len(self.assembler.basic_forms):
            #    self.random(True)

        if self.iteration % 8 == 0:
            if self.iteration % 1000 == 0:
                self.full_paint = True
            self.canvas.update()

    @showException
    def on_paint(self, painter):
        self.paint_changes(painter)

    ###################################################################
    # Data -> UI.

    def set_grid(self, value):
        if value is None:
            return
        self.grid = value
        self.grid_box.setChecked(self.grid)
        self.full_paint = True
        self.canvas.update()

    def set_knot(self, value):
        if value is None:
            return
        self.knot = value
        self.knot_box.setChecked(self.knot)
        self.full_paint = True
        self.canvas.update()

    def set_labels(self, value):
        if value is None:
            return
        self.labels = value
        self.labels_box.setChecked(self.labels)
        self.full_paint = True
        self.canvas.update()

    def set_border(self, value):
        if value is None:
            return
        self.border = value
        self.border_box.setChecked(self.border)
        self.full_paint = True
        self.canvas.update()

    def set_fill(self, value):
        if value is None:
            return
        self.fill = value
        self.fill_box.setChecked(self.fill)
        self.full_paint = True
        self.canvas.update()

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
        self.full_paint = True
        self.canvas.update()

    def set_thickness(self, value):
        if value is None:
            return
        self.thickness = value
        self.thickness_spin.setValue(self.thickness)
        self.full_paint = True
        self.canvas.update()

    def set_size(self, sz):
        if sz is None:
            return
        self.width = sz.width()
        self.height = sz.height()
        self.full_paint = True
        self.canvas.update()

    ###################################################################
    # Starting a new tiling.

    def reset(self, index = 0):
        try:
            self.config = Config(self.tilings_combo.currentText())
            self.error = None
        except Exception as e:
            self.config = Config("---- grid=0 background=fff foreground=f66")
            self.error = str(e)
            self.full_paint = True
            self.canvas.update()

        self.set_fill(self.config.fill)
        self.set_border(self.config.border)
        self.set_labels(self.config.labels)
        self.set_grid(self.config.grid)

        self.background = alloc_color(self.config.background)
        self.foreground = alloc_color(self.config.foreground)
        self.colors = [ alloc_color(item) for item in self.config.colors ]

        point_set = { }
        yr = int( self.height/self.scale/4 )
        xr = int( self.width/self.scale/4 )
        if self.labels:
            bound = self.scale * 3
            for y in range(-yr,yr):
                for x in range(-xr,xr):
                    point = self.pos(x*2,y*2)
                    if point.x > bound and point.x < self.width-bound and \
                       point.y > bound and point.y < self.height-bound-40:
                        point_set[(y,x)] = True
        else:
            bound = self.scale * 3
            for y in range(-yr,yr):
                for x in range(-xr,xr):
                    point = self.pos(x*2,y*2)
                    if point.x > -bound and point.x < self.width+bound and \
                       point.y > -bound and point.y < self.height+bound:
                        point_set[(y,x)] = True


        self.randomizing = False
        self.iteration = 0
        self.shapes = { }
        self.polys = { }
        self.full_paint = True
        self.assembler = Assembler(self.config.connections, Config.compatabilities,
                                   self.config.forms, self.config.probabilities, point_set)
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
                sides = random.choice([4,6])

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

        for i in range(len(self.assembler.connections)):
            yy, xx = self.assembler.connections[i][:2]
            symbol = self.assembler.forms[form_number][i]
            if symbol in '-': continue

            edge = self.pos(xx,yy,0)
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

            if symbol in 'ABCD':
                poke = 0.15 # 0.3 #r
            elif symbol in 'abcd':
                poke = -0.15 # -0.3 #-r
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
                    if form[i] not in '-' and \
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
                color = self.colors[self.assembler.form_id[form_number] % len(self.colors)]

            if self.fill:
                if not erase:
                    self.setPaintColors(painter, None, color)
                painter.drawPolygon(*val2pt(poly))

            if self.knot:
                self.setPaintColors(painter, color, None)
                for link, line1, line2 in links:
                    if not erase:
                        self.setPaintColors(painter, None, self.foreground)
                    painter.drawPolygon(*val2pt(link))
                    if not erase:
                        self.setPaintColors(painter, None, color)
                    self.setPaintColors(painter, color, None)
                    #painter.drawPolygon(*val2pt(link))
                    painter.drawLines(*val2pt(line1))
                    painter.drawLines(*val2pt(line2))
                    #painter.drawLine(*val2pt(connections[i][-1]+connections[j][0]))
                    #painter.drawLine(*val2pt(connections[j][-1]+connections[i][0]))

            if self.border:
                if not erase:
                    self.setPaintColors(painter, self.foreground, None)
                painter.drawPolygon(*val2pt(poly))

    def draw_text(self, painter, x, y, padding, with_rect, text):
        alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop | QtCore.Qt.TextWordWrap
        r = painter.boundingRect(x, y, self.width - x, self.height - y, alignment, text)
        r.adjust(-padding, -padding, padding * 2, padding * 2)
        if with_rect:
            painter.drawRect(r)
        alignment = QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap
        painter.drawText(r, alignment, text)
        return r.right() + padding * 2

    def repaint_all(self, painter):
        self.setPaintColors(painter, self.foreground, self.background)
        painter.drawRect(0, 0, self.width, self.height)

        if self.labels:
            fontSize = 16
            padding = 6
            self.setPaintFont(painter, fontSize)
            x = padding * 2
            y = self.height - fontSize - padding * 4
            if self.config.name:
                self.setPaintColors(painter, self.foreground, self.background)
                x = self.draw_text(painter, x, y, padding, False, self.config.name)
            for i, form in enumerate(self.assembler.basic_forms):
                self.setPaintColors(painter, self.foreground, self.colors[i])
                x = self.draw_text(painter, x, y, padding, True, form)

        if self.grid:
            self.setPaintColors(painter, alloc_color("eee"), None)
            f = 4.0 / len(self.config.connections)
            for (y,x) in self.assembler.point_set.keys():
                poly = [ ]
                for i in range(len(self.config.connections)):
                    a = self.config.connections[i-1]
                    b = self.config.connections[i]
                    poly.append((self.pos(x*2+(a[0]+b[0])*f,y*2+(a[1]+b[1])*f)).int_xy())

                painter.drawPolygon(*val2pt(poly))

        for (y,x), form_number in self.assembler.tiles.items():
            self.draw_poly(y,x,form_number,painter)

        if self.error:
            self.setPaintColors(painter, QtGui.QColor(0,0,0), QtGui.QColor(255,240,240))
            self.setPaintFont(painter, 24)
            painter.drawText(0, 0, self.width, self.height, QtCore.Qt.AlignCenter | QtCore.Qt.TextWordWrap, self.error)


    def paint_changes(self, painter):
        if self.full_paint:
            self.full_paint = False
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


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    ui = Interface()
    ui.window.show()
    app.exec()
    sys.exit(0)

    # Just some phd stuff...
    interface = Interface()
    interface.window.show_all()

    base = 2
    chars = " 1"
    n = len(connections)
    done = { }

    for i in range(1, base ** n):
        result = ""
        for j in range(n):
            result += chars[(i / (base ** j)) % base]
        if normalize(result) in done or normalize(result.swapcase()) in done: continue
        print(result)
        done[normalize(result)] = True

        interface.tilings_combo.entry.set_text("'"+result+"', width=350, height=400")
        interface.reset()

        while gtk.events_pending():
            gtk.main_iteration()

        if interface.assembler.dirty:
            print("--- failed")
            continue

        interface.scaled_pixbuf.save("/tmp/T" + result.replace(" ","-") + ".png", "png")
