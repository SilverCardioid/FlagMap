import glob
import math
import os
import re
import traceback
import typing as ty
import xml.etree.ElementTree as ET

import cairocffi as cairo
from cairosvg.parser import Tree as csvg_Tree
from cairosvg.surface import SVGSurface as csvg_Surface
try: # shapely 1.7+
	from shapely.ops import polylabel
except ImportError: # shapely 1.6
	from shapely.algorithms.polylabel import polylabel
from shapely.geometry import Polygon
import rdp

import cairopath
from helpers import separate

xmlns = '{http://www.w3.org/2000/svg}'

class FlagMap:
	mapOptions = {
		'height': None,
		'backgroundColor': '#444',
		'mapColor': '#ddd',
		'strokeColor': '#aaa',
		'strokeWidth': 1,
		'flagOpacity': 1,
		'preserveAspectRatio': True,
		'smallFlag': False,
		'smallFlagSize': None,
		'smallFlagThreshold': None,
		'smallFlagSeparate': True,
		'smallFlagSpacing': None,
		'lerpPOI': 0.5
	}

	def __init__(self, mapPath:str, mapOptions:dict = {}, *, printProgress:bool = True):
		self.mapPath = mapPath
		self.printProgress = printProgress
		self.flags = {}
		self.smallFlags = {}
		self.mapOptions = {key: mapOptions.get(key, val) for key,val in FlagMap.mapOptions.items()}
		if self.printProgress:
			for key in mapOptions.keys():
				if key not in FlagMap.mapOptions:
					print('Warning: unknown mapOption ' + key)

		if self.printProgress:
			print('Reading ' + os.path.basename(mapPath))
		mapSVG = ET.parse(mapPath)
		self.map = mapSVG.getroot()
		width = re.match('^(\d*\.?\d+(?:e\d+)?)(?:px)?$', self.map.attrib['width'])
		height = re.match('^(\d*\.?\d+(?:e\d+)?)(?:px)?$', self.map.attrib['height'])
		if not width or not height:
			raise Exception(f'couldn\'t parse intrinsic size: {self.map.attrib["width"]} × {self.map.attrib["height"]}')
		self.intrinsicWidth = float(width[1])
		self.intrinsicHeight = float(height[1])

		if self.mapOptions['height'] is None:
			self.mapOptions['height'] = self.intrinsicHeight
		if self.mapOptions['smallFlagSize'] is None:
			self.mapOptions['smallFlagSize'] = self.mapOptions['height']/40
		if self.mapOptions['smallFlagSpacing'] is None:
			self.mapOptions['smallFlagSpacing'] = self.mapOptions['smallFlagSize']/5

	def draw(self, outputPath:str):
		scale = self.mapOptions['height']/self.intrinsicHeight
		mapWidth = round(scale*self.intrinsicWidth)
		mapHeight = round(scale*self.intrinsicHeight)
		canvas = cairopath.Canvas(mapWidth, mapHeight, self.mapOptions['backgroundColor'])
		canvas.scale(scale)

		try:
			smallFlagsToDraw = []
			for child in self.map.iter(xmlns + 'path'):
				id = child.attrib['id'] if 'id' in child.attrib else None
				border = Border(id, child.attrib['d'], _printProgress=self.printProgress)
				border.parse(canvas) # draws the border for the following fill/stroke calls
				if id and id in self.flags:
					flag = self.flags[id]

					makeSmall = flag.flagOptions['smallFlag'] or \
					            (id not in self.smallFlags and self.mapOptions['smallFlagThreshold'] and
					             border.width*border.height < self.mapOptions['smallFlagThreshold']**2)
					if makeSmall:
						canvas.fill(self.mapOptions['mapColor'], keep=True) \
						      .stroke(self.mapOptions['strokeColor'], width=self.mapOptions['strokeWidth']/scale)
						centerX, centerY = border.getCenter(self.mapOptions['lerpPOI'])
						smallFlagsToDraw.append({'flag': flag, 'x': centerX, 'y': centerY})
						if id in self.smallFlags: # flagOptions['smallFlag'] overrides self.smallFlags
							continue
					else:
						flag.read()
						scaleX, scaleY = border.width/flag.width, border.height/flag.height
						x, y = border.minX, border.minY
						if self.mapOptions['preserveAspectRatio'] and scaleX != scaleY:
							if scaleX > scaleY:
								scaleY = scaleX
								y -= (scaleY*flag.height - border.height)*flag.flagOptions['keyPoint'][1]
							else:
								scaleX = scaleY
								x -= (scaleX*flag.width - border.width)*flag.flagOptions['keyPoint'][0]
						with canvas.clip(): # uses last drawing (border)
							flag.draw(canvas, x, y, scaleX, scaleY, small=False)
						border.draw(canvas)
						canvas.stroke(self.mapOptions['strokeColor'], width=self.mapOptions['strokeWidth']/scale)

				elif id: # no flag, or flag from self.smallFlags
					canvas.fill(self.mapOptions['mapColor'], keep=True) \
					      .stroke(self.mapOptions['strokeColor'], width=self.mapOptions['strokeWidth']/scale)
				else: # no id; just draw stroke
					canvas.stroke(self.mapOptions['strokeColor'], width=self.mapOptions['strokeWidth']/scale)

				if id in self.smallFlags:
					centerX, centerY = border.getCenter(self.mapOptions['lerpPOI'])
					smallFlagsToDraw.append({'flag': self.smallFlags[id], 'x': centerX, 'y': centerY})


			if len(smallFlagsToDraw) > 0:
				if self.mapOptions['smallFlagSeparate']:
					rects = []
					sep = self.mapOptions['smallFlagSpacing']
					for arr in smallFlagsToDraw:
						flag = arr['flag']
						flag.read()
						flag.scale = flag.flagOptions['smallFlagSize']/math.sqrt(flag.width*flag.height)
						arr['width'], arr['height'] = flag.scale*flag.width, flag.scale*flag.height
						rw, rh = arr['width'] + sep, arr['height'] + sep
						rx, ry = arr['x'] - rw/2, arr['y'] - rh/2
						rects.append(separate.Rectangle(rx, ry, rw, rh))

					if self.printProgress:
						print('Separating')
					stepper = separate.Separation(rects)
					while separate.Rectangle.has_overlaps(stepper.rectangles):
						stepper.step()
					if self.printProgress:
						movement = separate.Rectangle.total_movement(stepper.rectangles)
						print(f'Total movement: {movement:g} px')

					for i, arr in enumerate(smallFlagsToDraw):
						flag = arr['flag']
						if self.printProgress and len(smallFlagsToDraw) > 0:
							print('Drawing ' + os.path.basename(flag.filePath))
						flag.draw(canvas, rects[i].midx - arr['width']/2, rects[i].midy - arr['height']/2,
						          flag.scale, small=True)

				else:
					for arr in smallFlagsToDraw:
						flag = arr['flag']
						flag.read()
						flag.scale = flag.flagOptions['smallFlagSize']/math.sqrt(flag.width*flag.height)
						x, y = arr['x'] - flag.scale*flag.width/2, arr['y'] - flag.scale*flag.height/2
						flag.draw(canvas, x, y, flag.scale, small=True)

		finally:
			canvas.export('png', outputPath)

	def addFlags(self, flags:ty.Dict[str, str], flagOptions:dict = {}, *,
	             small:bool = False, overwrite:bool = True):
		target = self.smallFlags if small else self.flags
		for id in flags:
			if id in target:
				if self.printProgress:
					print('Flag for ' + id + ('' if overwrite else ' not') + ' overwritten')
				if not overwrite: continue
			target[id] = Flag(id, flags[id], flagOptions, _mapOptions=self.mapOptions, _printProgress=self.printProgress)

		return self

	def addFlagsFromFolder(self, folder:str, flagOptions:dict = {}, *,
	                       small:bool = False, overwrite:bool = False, recursive:bool = False):
		wildcard = '**/*' if recursive else '*'
		svgs = glob.glob(os.path.join(folder, wildcard + '.svg'))
		pngs = glob.glob(os.path.join(folder, wildcard + '.png'))
		target = self.smallFlags if small else self.flags
		for file in svgs + pngs:
			id = os.path.splitext(os.path.basename(file))[0]
			if id in target:
				if file[-4:].lower() == '.png' and target[id].fileType == '.svg':
					# Silently skip PNG if SVG exists
					continue
				elif self.printProgress:
					print('Flag for ' + id + ('' if overwrite else ' not') + ' overwritten')
				if not overwrite: continue
			target[id] = Flag(id, file, flagOptions, _mapOptions=self.mapOptions, _printProgress=self.printProgress)
		return self


class Flag:
	flagOptions = {
		'strokeColor': None,
		'strokeWidth': None,
		'smallFlag': None,
		'smallFlagSize': None,
		'flagOpacity': None,
		'keyPoint': (0.5, 0.5),
		'outline': [(0,0), (1,0), (1,1), (0,1)]
	}

	def __init__(self, id:str, filePath:str, flagOptions:dict = {}, *, _mapOptions={}, _printProgress=True):
		self.printProgress = _printProgress
		self.id = id
		self.filePath = filePath
		self.fileType = os.path.splitext(self.filePath)[1].lower()
		if not os.path.exists(filePath):
			raise FileNotFoundError(filePath)
		self.surface = None
		self.ratio = 1
		self.flagOptions = {key: flagOptions.get(key, val) for key,val in Flag.flagOptions.items()}
		for key in self.flagOptions:
			if self.flagOptions[key] is None and key in _mapOptions:
				self.flagOptions[key] = _mapOptions[key]
		if self.printProgress:
			for key in flagOptions.keys():
				if key not in Flag.mapOptions:
					print('Warning: unknown mapOption ' + key)

	def read(self):
		if self.surface is None:
			if self.printProgress:
				print('Reading ' + os.path.basename(self.filePath))
			if self.fileType == '.svg':
				tree = csvg_Tree(url=self.filePath)
				surface = csvg_Surface(tree, output=None, dpi=96)
				self.width, self.height = surface.width, surface.height
				self.surface = surface.cairo
			elif self.fileType == '.png':
				self.surface = cairo.ImageSurface.create_from_png(self.filePath)
				self.width, self.height = self.surface.get_width(), self.surface.get_height()
			else:
				raise Exception('unsupported flag file type: ' + self.fileType)
		return self

	def draw(self, canvas:cairopath.Canvas, x:float = 0, y:float = 0,
	         sx:float = 1, sy:ty.Optional[float] = None, *, small:bool = False):
		if not self.surface:
			self.read()
		if not sy:
			sy = sx
		if small and self.flagOptions['outline'] and self.flagOptions['strokeWidth'] > 0:
			w, h = self.width*sx, self.height*sy
			outline = self.flagOptions['outline']
			path = canvas.path()
			path.M(x + w*outline[0][0], y + h*outline[0][1])
			for coord in outline[1:]:
				path.L(x + w*coord[0], y + h*coord[1])
			path.z().stroke(self.flagOptions['strokeColor'], width=2*self.flagOptions['strokeWidth'])

		with canvas.translate(x, y).scale(sx, sy):
			if not small:
				canvas.rect(self.width, self.height).fill('#fff')
			canvas.context.set_source_surface(self.surface, 0, 0)
			if not small and self.flagOptions['flagOpacity'] < 1:
				canvas.context.paint_with_alpha(self.flagOptions['flagOpacity'])
			else:
				canvas.context.paint()

		self.surface = None


class Border:
	def __init__(self, id:str, d:str, *, _printProgress=True):
		self.printProgress = _printProgress
		self.id = id
		self.d = d
		self.vertices = None

	def draw(self, canvas:cairopath.Canvas):
		obj = cairopath.StringParser(canvas, self.d)
		obj.draw()
		self.vertices = obj.vertices

	def parse(self, canvas:cairopath.Canvas):
		self.draw(canvas)

		# vertices = [(x,y), (angle,angle), (x,y), ...]
		self.minX = self.maxX = self.vertices[0][0]
		self.minY = self.maxY = self.vertices[0][1]
		vGen = (v for i,v in enumerate(self.vertices) if i%2 == 0)
		for v in vGen:
			if v is not None:
				self.minX = min(self.minX, v[0]); self.maxX = max(self.maxX, v[0])
				self.minY = min(self.minY, v[1]); self.maxY = max(self.maxY, v[1])
		self.width = self.maxX - self.minX
		self.height = self.maxY - self.minY

	def getCenter(self, lerpPOI:float = 0):
		centerX, centerY = (self.minX + self.maxX)/2, (self.minY + self.maxY)/2

		if lerpPOI > 0:
			try:
				polys = [[]]
				for i, v in enumerate(self.vertices):
					if i % 2 == 0:
						polys[-1].append(v)
					elif v is None:
						polys.append([])
				bestPoint = None
				bestRadius = 0
				for poly in polys:
					if len(poly) >= 3:
						polyObj = Polygon(poly)
						point = polylabel(polyObj)
						radius = point.distance(polyObj.exterior)
						if radius > bestRadius:
							bestPoint = point
							bestRadius = radius
				centerX = lerpPOI*bestPoint.x + (1 - lerpPOI)*centerX
				centerY = lerpPOI*bestPoint.y + (1 - lerpPOI)*centerY
			except:
				print(f'Error getting POI for outline of {self.id}:')
				traceback.print_exc()

		return (centerX, centerY)


class ImageMap:
	def __init__(self, mapPath:str, epsilon:float = 5, relEpsilon:float = 1/3,
	             nameFunction:ty.Optional[ty.Callable] = None):
		self.mapPath = mapPath
		self.epsilon = epsilon
		self.relEpsilon = relEpsilon
		self.nameFunction = nameFunction
		self._flagmap = FlagMap(mapPath, printProgress=False)
		self._canvas = cairopath.Canvas(round(self._flagmap.intrinsicWidth), round(self._flagmap.intrinsicHeight))

	def list(self, outputPath:str):
		with open(outputPath, 'w', encoding='UTF-8') as f:
			f.write('<imagemap>\n')
			f.write('File:{}|{}px|thumb|right\n'.format(os.path.basename(self.mapPath), round(self._flagmap.intrinsicHeight)))
			for child in self._flagmap.map.iter(xmlns + 'path'):
				id = child.attrib['id'] if 'id' in child.attrib else None
				if id:
					name = self.nameFunction(id) if self.nameFunction else id
					border = Border(id, child.attrib['d'])
					self._canvas.context.new_path() # reset current point
					border.parse(self._canvas)
					poly = []
					for i, v in enumerate(border.vertices):
						if i % 2 == 0:
							poly.append(v)
						elif v is None:
							self.poly(f, poly, name)
							poly = []
					self.poly(f, poly, name)
			
			f.write('</imagemap>')

	def poly(self, file:ty.TextIO, poly:ty.List[ty.Tuple[float, float]], link:str):
		epsilon = self.epsilon or math.inf
		if (self.epsilon or self.relEpsilon) and len(poly) > 2:
			# Simplify using RDP
			if self.relEpsilon:
				# Limit epsilon to fraction of polygon width and height
				(minX, minY), (maxX, maxY) = poly[0], poly[0]
				for p in poly:
					minX, minY = min(minX, p[0]), min(minY, p[1])
					maxX, maxY = max(maxX, p[0]), max(maxY, p[1])
				epsilon = max(1, min([self.epsilon, (maxX-minX)*self.relEpsilon, (maxY-minY)*self.relEpsilon]))
			# Use closed version of path
			poly = poly + [poly[0]]
			poly = rdp.rdp(poly, epsilon=epsilon)
			del poly[-1]

		if len(poly) > 2:
			# Write polygon to file
			file.write('poly ')
			for p in poly:
				file.write('{} {} '.format(round(p[0]), round(p[1])))
			file.write('[[{}]]\n'.format(link))
