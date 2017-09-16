#!/usr/bin/env python

#    Copyright (C) 2004 Paul Harrison
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

     A number of extra paramters can also be supplied:

         border : True/False : draw tile borders or not
         fill : True/False : fill tile or not
         thickness : the thickness of the border
         width : minimum width of diagram
         height : minimum height of diagram
         colors : a list of colors
            background color,edge-color,tile-1-color,tile-2-color...
         grid : True/False : draw a grid
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


  TODO: don't backtrack areas outside current locus
        (difficulty: accidentally creating disconnected islands)

  TODO: (blue sky) 3D, third dimension == time
  TODO: allowances: 3 of this, 2 of that, etc.
"""

try:
    import psyco
    psyco.profile()
except:
    pass

__version__ = '0.8'

import sys, os, random, math, functools
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
import PyQt5.QtWidgets as QtWidgets

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


# ========================================================================
# Constants

# Hexagonal connection pattern:
#
#     o o
#   o * o
#   o o
#
# (all points remain on a square grid, but a regular hexagon pattern
#  can be formed by a simple linear transformation)

connections_6 = [ (-1, 0, 3), (-1, 1, 4), (0, 1, 5), (1, 0, 0), (1, -1, 1), (0, -1, 2) ]
# [ (y, x, index of reverse connection) ]
x_mapper_6 = Point(1.0, 0.0)
y_mapper_6 = Point(0.5, 0.75**0.5)

connections_4 = [ (-1,0,2), (0,1,3), (1,0,0), (0,-1,1) ]
x_mapper_4 = Point(1.0, 0.0)
y_mapper_4 = Point(0.0, 1.0)



# What edge type connects with what?
# (a tile is represented as a string of 6 characters representing the 6 edges)
compatabilities = {
    '-':'-',
    'A':'a', 'a':'A', 'B':'b', 'b':'B', 'c':'C', 'C':'c', 'd':'D', 'D':'d',
    '1':'1', '2':'2', '3':'3', '4':'4',  '_':'_'
}


# Some cool tile sets people have found
catalogue = [
    "--33Aa -33-Aa",
    "--33Aa/000 -33-Aa/000 colors=fff,fff border=0 grid=0",
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


default_colors=['fff','000', '8ff', 'f44', 'aaf','449', 'ff0088', 'ff4088', 'ff4040', 'ff00ff', '40c0ff']

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


# ========================================================================
# Utility functions

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

def parse_colors(self, c):
    pass

def parse_bool(self, c):
    if '=' not in c:
        return False
    try:
        m, b = c.split('=')
        setattr(self, m, bool(b))
        return True
    except Exception as e:
        return False

def parse_float(self, c):
    if '=' not in c or '.' not in c:
        return False
    try:
        m, f = c.split('=')
        setattr(self, m, float(f))
        return True
    except Exception as e:
        return False

def parse_int(self, c):
    if '=' not in c:
        return False
    try:
        m, i = c.split('=')
        setattr(self, m, int(i))
        return True
    except Exception as e:
        return False

def parse_text(self, c):
    if '=' not in c:
        return False
    try:
        m, t = c.split('=')
        setattr(self, m, t)
        return True
    except Exception as e:
        return False

def parse_array_colors(self, c):
    if '=' not in c:
        return False
    try:
        m, colors_text = c.split('=')
        colors = []
        for color_text in colors_text.split(','):
            colors.append(color_text)
        setattr(self, m, colors)
        return True
    except Exception as e:
        return False


# =========================================================================

class Config:
    def __init__(self, cfg):
        self.colors = []
        self.border = True
        self.fill = True
        self.thickness = 1.0
        self.width = -1
        self.height = -1
        self.grid = True
        self.labels = False
        self.forms = []
        self.name = ""

        for c in cfg.split():
            for parse in (parse_float, parse_int, parse_array_colors, parse_bool, parse_text):
                if parse(self, c):
                    break
            else:
                self.forms.append(c)

        self.colors += default_colors[len(self.colors):]

        if len(self.forms) < 1: raise Exception("Not enough forms")

        self.probabilities = [1] * len(self.forms)

        for item in self.forms:
            if type(item) != type(""):
                raise Exception("Form #d is not text (%s)" % (self.forms.index(item)+1, item))

        for i in range(len(self.forms)):
            if "/" in self.forms[i]:
                self.forms[i], self.colors[i%(len(self.colors)-2)+2] = self.forms[i].split("/",1)
            if "@" in self.forms[i]:
                self.forms[i], count = self.forms[i].split("@",1)
                self.probabilities[i] = int(count)

        if len(self.forms[0]) == 4:
            self.connections = connections_4
            self.x_mapper = x_mapper_4
            self.y_mapper = y_mapper_4
        else:
            self.connections = connections_6
            self.x_mapper = x_mapper_6
            self.y_mapper = y_mapper_6

        for item in self.forms:
            if len(item) != len(self.connections):
                raise Exception("Incorrect connection length for item #%d (%s)" % (self.forms.index(item)+1, item))
            for edge in item:
                if edge not in compatabilities:
                    raise Exception("No compatible conection for form #%d (%s)" % (self.forms.index(item)+1, item))

# ========================================================================


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

        for id, form in enumerate(forms):
            current = form
            for i in range(len(self.connections)):
                if current not in self.forms:
                    self.forms.append(current)
                    self.form_id.append(id)
                    self.rotation.append(i)
                    self.probabilities.append(probabilities[id])
                current = current[1:] + current[0]

        self.tiles = { }   # (y,x) -> form number

        self.dirty = { }   # (y,x) -> True   -- Possible sites for adding tiles

        self.options_cache = { }   # pattern -> [form_ids]

        self.dead_loci = set([ ]) # [ {(y,x)->form number} ]

        self.history = [ ]

        self.total_y = 0
        self.total_x = 0

        self.changes = { }

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


class Canvas(QtWidgets.QFrame):

    painting = QtCore.pyqtSignal(['QPainter'])
    resizing = QtCore.pyqtSignal(['QSize'])

    def __init__(self):
        QtWidgets.QFrame.__init__(self)

    def paintEvent(self, event):
        painter = QtGui.QPainter()
        painter.begin(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        self.painting.emit(painter)
        painter.end()

    def resizeEvent(self, event):
        self.resizing.emit(event.size())


# ========================================================================


class Interface(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.iteration = 0
        self.width = 600
        self.height = 600
        self.scale = 6
        self.thickness = 2
        self.knot = False
        self.randomizing = False
        self.iteration = 0
        self.shapes = { }
        self.polys = { }
        self.assembler = None
        self.timer = None

        self.canvas = Canvas()
        self.canvas.painting.connect(self.on_paint)
        self.canvas.resizing.connect(self.on_size)
        self.canvas.resize(self.width, self.height)
        self.canvas.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.canvas.setLineWidth(1)
        self.canvas.setFrameStyle(Canvas.Box)

        self.diag_combo = QtWidgets.QComboBox()
        self.diag_combo.setEditable(True)
        self.diag_combo.completer().setCaseSensitivity(QtCore.Qt.CaseSensitive)
        for item in catalogue:
            self.diag_combo.addItem(item)
        self.diag_combo.currentIndexChanged.connect(self.on_reset)

        knot_box = QtWidgets.QCheckBox("Draw Knot")
        knot_box.setChecked(False)
        knot_box.stateChanged.connect(self.on_knot_changed)

        scale_label = QtWidgets.QLabel('Size:')
        scale_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        scale_spin = QtWidgets.QSpinBox()
        scale_spin.setSingleStep(1)
        scale_spin.setRange(3, 50)
        scale_spin.setValue(self.scale)
        scale_spin.valueChanged.connect(self.on_set_scale)

        thickness_label = QtWidgets.QLabel('Thickness:')
        thickness_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        thickness_spin = QtWidgets.QSpinBox()
        thickness_spin.setSingleStep(1)
        thickness_spin.setRange(1, 8)
        thickness_spin.setValue(self.thickness)
        thickness_spin.valueChanged.connect(self.on_set_thickness)

        random_button = QtWidgets.QPushButton('Random')
        random_button.clicked.connect(self.on_random)

        reset_button = QtWidgets.QPushButton('Restart')
        reset_button.clicked.connect(self.on_reset)

        hbox = QtWidgets.QHBoxLayout()
        hframe = QtWidgets.QFrame()
        hframe.setLayout(hbox)
        hbox.addWidget(knot_box)
        hbox.addWidget(reset_button)
        hbox.addWidget(random_button)
        hbox.addWidget(scale_label)
        hbox.addWidget(scale_spin)
        hbox.addWidget(thickness_label)
        hbox.addWidget(thickness_spin)

        vbox = QtWidgets.QVBoxLayout()
        vframe = QtWidgets.QFrame()
        vframe.setLayout(vbox)
        vbox.addWidget(self.diag_combo)
        vbox.addWidget(hframe)
        vbox.addWidget(self.canvas)

        self.window = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout()
        self.window.setLayout(grid)
        self.window.setMinimumSize(600,600)
        self.window.setWindowTitle('Ghost Diagrams')
        grid.addWidget(vframe)

        self.set_scale(scale_spin.value())
        self.reset()

    ###################################################################
    # Event handlers.

    @QtCore.pyqtSlot('QSize')
    def on_size(self, sz):
        self.update_size(sz)
        self.reset()

    def on_set_scale(self, value):
        self.set_scale(value)
        self.reset()

    def on_set_thickness(self, value):
        self.set_thickness(value)
        self.canvas.update()

    def on_knot_changed(self, state):
        self.knot = state
        self.reset()

    def on_reset(self, index = 0):
        self.reset(index)

    def on_new_diag(self, text):
        self.reset()

    def on_random(self):
        self.random()

    def on_idle(self):
        if not self.assembler.iterate():
            self.timer.stop()
            self.timer = None
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
            self.canvas.update()

    ###################################################################
    # Processing.

    def reset(self, index = 0):
        try:
            self.config = Config(self.diag_combo.currentText())
        except Exception as e:
            QtWidgets.QErrorMessage(self.window).showMessage(str(e))
            self.config = Config("---- grid=0 colors=f66")

        self.colors = [ alloc_color(item) for item in self.config.colors ]

        point_set = { }
        yr = int( self.height/self.scale/4 )
        xr = int( self.width/self.scale/4 )
        if self.config.labels:
            bound = self.scale * 3
            for y in range(-yr,yr):
                for x in range(-yr,xr):
                    point = self.pos(x*2,y*2)
                    if point.x > bound and point.x < self.width-bound and \
                       point.y > bound and point.y < self.height-bound-90:
                        point_set[(y,x)] = True
        else:
            bound = self.scale * 3
            for y in range(-yr,yr):
                for x in range(-yr,xr):
                    point = self.pos(x*2,y*2)
                    if point.x > -bound and point.x < self.width+bound and \
                       point.y > -bound and point.y < self.height+bound:
                        point_set[(y,x)] = True


        self.randomizing = False
        self.iteration = 0
        self.shapes = { }
        self.polys = { }
        self.assembler = Assembler(self.config.connections, compatabilities,
                                   self.config.forms, self.config.probabilities, point_set)
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.on_idle)
        self.timer.start()

    def run(self, app):
        self.window.show()
        app.exec()


    def set_scale(self, value):
        self.scale = value

    def set_thickness(self, value):
        self.thickness = value

    def update_size(self, sz):
        self.width = sz.width()
        self.height = sz.height()

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
            if symbol in ' -': continue

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

            result.append( (out * (1.0/out.length()), points, 0.5)) #0.625))
            connections[i] = points
            # Note: set constant to ~0.35 for old-style circular look

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
                    if form[i] not in ' -' and \
                       form.count(form[i]) == 1 and \
                       (compatabilities[form[i]] == form[i] or \
                        form.count(compatabilities[form[i]])%2 == 0):
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
                color = 0
            else:
                color = self.assembler.form_id[form_number] % (len(self.colors)-2) + 2

            def setStyle(painter, border, fill):
                if border:
                    pen = QtGui.QPen(border)
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

            if self.config.fill:
                setStyle(painter, None, self.colors[color])
                painter.drawPolygon(*val2pt(poly))

            if self.knot:
                setStyle(painter, self.colors[color], None)
                for link, line1, line2 in links:
                    if not erase:
                        setStyle(painter, None, self.colors[1])
                    painter.drawPolygon(*val2pt(link))
                    if not erase:
                        setStyle(painter, None, self.colors[color])
                    setStyle(painter, self.colors[color], None)
                    #painter.drawPolygon(*val2pt(link))
                    painter.drawLines(*val2pt(line1))
                    painter.drawLines(*val2pt(line2))
                    #painter.drawLine(*val2pt(connections[i][-1]+connections[j][0]))
                    #painter.drawLine(*val2pt(connections[j][-1]+connections[i][0]))

            if self.config.border:
                if not erase:
                    setStyle(painter, self.colors[1], None)
                painter.drawPolygon(*val2pt(poly))

    @QtCore.pyqtSlot('QPainter')
    def on_paint(self, painter):
        if not self.assembler.tiles:
            return

        painter.setPen(self.colors[0])

        if self.config.labels and False:
            font = pango.FontDescription("mono bold 36")
            painter.setPen(self.colors[1])

            for i, form in enumerate(self.assembler.basic_forms):
                layout = self.canvas.create_pango_layout(" "+form.replace(" ","-")+" ")
                layout.set_font_description(font)
                x = (i+1)*(len(form)+3)*30
                y = (self.height-70)
                width, height = layout.get_pixel_size()
                self.pixmap.draw_rectangle(self.gc, True, x-6,y-6, width+12,height+12)
                self.pixmap.draw_layout(self.gc, x,y, layout, self.colors[1], self.colors[i+2])

        if self.config.grid:
            pen = QtGui.QPen()
            pen.setWidth(max(1,int(self.thickness * self.config.thickness)))
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            pen.setColor(alloc_color("eee"))
            painter.setPen(pen)
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

    def on_paint_changes(self,painter):
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
        def merde(result):
            result.clear()
            previous = '1234' + 'aAbBcCdD' #* 3
            for edge_count in edge_counts:
                item = ['-']*(sides-edge_count)
                for j in range(edge_count):
                    selection = random.choice(previous)
                    previous += compatabilities[selection]*6 #12
                    item.append(selection)

                random.shuffle(item)
                item = normalize(''.join(item))
                if item in result: return True
                result.append(item)

            all = ''.join(result)
            for a, b in compatabilities.items():
                if a in all and b not in all: return True
            return False
        while merde(result):
            pass

        self.diag_combo.addItem(' '.join(result))
        self.diag_combo.setCurrentIndex(self.diag_combo.count()-1)
        self.reset()
        self.randomizing = True


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    Interface().run(app)
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

        interface.diag_combo.entry.set_text("'"+result+"', width=350, height=400")
        interface.reset()

        while gtk.events_pending():
            gtk.main_iteration()

        if interface.assembler.dirty:
            print("--- failed")
            continue

        interface.scaled_pixbuf.save("/tmp/T" + result.replace(" ","-") + ".png", "png")
