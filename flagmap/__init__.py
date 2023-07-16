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
from . import separate

xmlns = '{http://www.w3.org/2000/svg}'

def _read_map(map_path:str) -> ty.Tuple[ET.Element, float, float]:
	map_svg = ET.parse(map_path)
	root = map_svg.getroot()
	width = re.match('^(\d*\.?\d+(?:e\d+)?)(?:px)?$', root.attrib['width'])
	height = re.match('^(\d*\.?\d+(?:e\d+)?)(?:px)?$', root.attrib['height'])
	if not width or not height:
		raise Exception(f'couldn\'t parse intrinsic size: {root.attrib["width"]} × {root.attrib["height"]}')
	return (root, float(width[1]), float(height[1]))

class FlagMap:
	map_options = {
		'height': None,
		'background_color': '#444',
		'map_color': '#ddd',
		'stroke_color': '#aaa',
		'stroke_width': 1,
		'flag_opacity': 1,
		'preserve_aspect_ratio': True,
		'small_flag': False,
		'small_flag_size': None,
		'small_flag_threshold': None,
		'small_flag_separate': True,
		'small_flag_spacing': None,
		'small_flag_position_lerp': 0.5
	}

	def __init__(self, map_path:str, options:dict = {}, *, print_progress:bool = True):
		self.map_path = map_path
		self.print_progress = print_progress
		self.flags = {}
		self.small_flags = {}
		self.map_options = {key: options.get(key, val) for key,val in FlagMap.map_options.items()}
		if self.print_progress:
			for key in options.keys():
				if key not in FlagMap.map_options:
					print('Warning: unknown map option ' + key)

		if self.print_progress:
			print('Reading ' + os.path.basename(map_path))
		map_svg = ET.parse(map_path)
		self.map, self.map_width, self.map_height = _read_map(map_path)

		if self.map_options['height'] is None:
			self.map_options['height'] = self.map_height
		if self.map_options['small_flag_size'] is None:
			self.map_options['small_flag_size'] = self.map_options['height']/40
		if self.map_options['small_flag_spacing'] is None:
			self.map_options['small_flag_spacing'] = self.map_options['small_flag_size']/5

	def draw(self, output_path:str):
		scale = self.map_options['height']/self.map_height
		width = round(scale*self.map_width)
		height = round(scale*self.map_height)

		ext = os.path.splitext(output_path)[1].lower()
		if ext not in ('.png', '.svg', '.pdf', '.ps'):
			raise ValueError('unsupported output format: ' + ext)

		surface_type = ext[1:]
		canvas = cairopath.Canvas(
			width, height, bgcolor=self.map_options['background_color'],
			surfacetype=surface_type, filename=output_path
		)
		canvas.scale(scale)

		try:
			small_flags_to_draw = []
			for child in self.map.iter(xmlns + 'path'):
				id = child.attrib['id'] if 'id' in child.attrib else None
				border = Border(id, child.attrib['d'], _print_progress=self.print_progress)
				border.parse(canvas) # draws the border for the following fill/stroke calls
				if id and id in self.flags:
					flag = self.flags[id]

					make_small = flag.flag_options['small_flag'] or \
					             (id not in self.small_flags and self.map_options['small_flag_threshold'] and
					              border.width*border.height < self.map_options['small_flag_threshold']**2)
					if make_small:
						canvas.fill(self.map_options['map_color'], keep=True) \
						      .stroke(self.map_options['stroke_color'], width=self.map_options['stroke_width']/scale)
						center_x, center_y = border.get_center(self.map_options['small_flag_position_lerp'])
						small_flags_to_draw.append({'flag': flag, 'x': center_x, 'y': center_y})
						if id in self.small_flags: # flag_options['small_flag'] overrides self.small_flags
							continue
					else:
						flag.read()
						scale_x, scale_y = border.width/flag.width, border.height/flag.height
						x, y = border.min_x, border.min_y
						if self.map_options['preserve_aspect_ratio'] and scale_x != scale_y:
							if scale_x > scale_y:
								scaley = scale_x
								y -= (scale_y*flag.height - border.height)*flag.flag_options['key_point'][1]
							else:
								scale_x = scale_y
								x -= (scale_x*flag.width - border.width)*flag.flag_options['key_point'][0]
						with canvas.clip(): # uses last drawing (border)
							flag.draw(canvas, x, y, scale_x, scale_y, small=False)
						border.draw(canvas)
						canvas.stroke(self.map_options['stroke_color'], width=self.map_options['stroke_width']/scale)

				elif id: # no flag, or flag from self.small_flags
					canvas.fill(self.map_options['map_color'], keep=True) \
					      .stroke(self.map_options['stroke_color'], width=self.map_options['stroke_width']/scale)
				else: # no id; just draw stroke
					canvas.stroke(self.map_options['stroke_color'], width=self.map_options['stroke_width']/scale)

				if id in self.small_flags:
					center_x, center_y = border.get_center(self.map_options['small_flag_position_lerp'])
					small_flags_to_draw.append({'flag': self.small_flags[id], 'x': center_x, 'y': center_y})


			if len(small_flags_to_draw) > 0:
				if self.map_options['small_flag_separate']:
					rects = []
					sep = self.map_options['small_flag_spacing']
					for arr in small_flags_to_draw:
						flag = arr['flag']
						flag.read()
						flag.scale = flag.flag_options['small_flag_size']/math.sqrt(flag.width*flag.height)
						arr['width'], arr['height'] = flag.scale*flag.width, flag.scale*flag.height
						rw, rh = arr['width'] + sep, arr['height'] + sep
						rx, ry = arr['x'] - rw/2, arr['y'] - rh/2
						rects.append(separate.Rectangle(rx, ry, rw, rh))

					if self.print_progress:
						print('Separating')
					stepper = separate.Separation(rects)
					while separate.Rectangle.has_overlaps(stepper.rectangles):
						stepper.step()
					if self.print_progress:
						movement = separate.Rectangle.total_movement(stepper.rectangles)
						print(f'Total movement: {movement:g} px')

					for i, arr in enumerate(small_flags_to_draw):
						flag = arr['flag']
						if self.print_progress and len(small_flags_to_draw) > 0:
							print('Drawing ' + os.path.basename(flag.file_path))
						flag.draw(canvas, rects[i].midx - arr['width']/2, rects[i].midy - arr['height']/2,
						          flag.scale, small=True)

				else:
					for arr in small_flags_to_draw:
						flag = arr['flag']
						flag.read()
						flag.scale = flag.flag_options['small_flag_size']/math.sqrt(flag.width*flag.height)
						x, y = arr['x'] - flag.scale*flag.width/2, arr['y'] - flag.scale*flag.height/2
						flag.draw(canvas, x, y, flag.scale, small=True)

		finally:
			if surface_type == 'png':
				# other surface types are saved automatically by Cairo
				canvas.export(surface_type, output_path)

	def add_flags(self, flags:ty.Dict[str, str], flag_options:dict = {}, *,
	             small:bool = False, overwrite:bool = True):
		target = self.small_flags if small else self.flags
		for id in flags:
			if id in target:
				if self.print_progress:
					print('Flag for ' + id + ('' if overwrite else ' not') + ' overwritten')
				if not overwrite: continue
			target[id] = Flag(id, flags[id], flag_options, _map_options=self.map_options, _print_progress=self.print_progress)

		return self

	def add_folder(self, folder:str, flag_options:dict = {}, *,
	               small:bool = False, overwrite:bool = False, recursive:bool = False):
		wildcard = '**/*' if recursive else '*'
		svgs = glob.glob(os.path.join(folder, wildcard + '.svg'))
		pngs = glob.glob(os.path.join(folder, wildcard + '.png'))
		target = self.small_flags if small else self.flags
		for file in svgs + pngs:
			id = os.path.splitext(os.path.basename(file))[0]
			if id in target:
				if file[-4:].lower() == '.png' and target[id].file_type == '.svg':
					# Silently skip PNG if SVG exists
					continue
				elif self.print_progress:
					print('Flag for ' + id + ('' if overwrite else ' not') + ' overwritten')
				if not overwrite: continue
			target[id] = Flag(id, file, flag_options, _map_options=self.map_options, _print_progress=self.print_progress)
		return self


class Flag:
	flag_options = {
		'stroke_color': None,
		'stroke_width': None,
		'small_flag': None,
		'small_flag_size': None,
		'flag_opacity': None,
		'key_point': (0.5, 0.5),
		'outline': [(0,0), (1,0), (1,1), (0,1)]
	}

	def __init__(self, id:str, file_path:str, options:dict = {}, *, _map_options={}, _print_progress=True):
		self.print_progress = _print_progress
		self.id = id
		self.file_path = file_path
		self.file_type = os.path.splitext(self.file_path)[1].lower()
		if not os.path.exists(self.file_path):
			raise FileNotFoundError(self.file_path)
		self.surface = None
		self.ratio = 1
		self.flag_options = {key: options.get(key, val) for key,val in Flag.flag_options.items()}
		for key in self.flag_options:
			if self.flag_options[key] is None and key in _map_options:
				self.flag_options[key] = _map_options[key]
		if self.print_progress:
			for key in options.keys():
				if key not in Flag.map_options:
					print('Warning: unknown map option ' + key)

	def read(self):
		if self.surface is None:
			if self.print_progress:
				print('Reading ' + os.path.basename(self.file_path))
			if self.file_type == '.svg':
				tree = csvg_Tree(url=self.file_path)
				surface = csvg_Surface(tree, output=None, dpi=96)
				self.width, self.height = surface.width, surface.height
				self.surface = surface.cairo
			elif self.file_type == '.png':
				self.surface = cairo.ImageSurface.create_from_png(self.file_path)
				self.width, self.height = self.surface.get_width(), self.surface.get_height()
			else:
				raise Exception('unsupported flag file type: ' + self.file_type)
		return self

	def draw(self, canvas:cairopath.Canvas, x:float = 0, y:float = 0,
	         sx:float = 1, sy:ty.Optional[float] = None, *, small:bool = False):
		if not self.surface:
			self.read()
		if not sy:
			sy = sx
		if small and self.flag_options['outline'] and self.flag_options['stroke_width'] > 0:
			w, h = self.width*sx, self.height*sy
			outline = self.flag_options['outline']
			path = canvas.path()
			path.M(x + w*outline[0][0], y + h*outline[0][1])
			for coord in outline[1:]:
				path.L(x + w*coord[0], y + h*coord[1])
			path.z().stroke(self.flag_options['stroke_color'], width=2*self.flag_options['stroke_width'])

		with canvas.translate(x, y).scale(sx, sy):
			if not small:
				canvas.rect(self.width, self.height).fill('#fff')
			canvas.context.set_source_surface(self.surface, 0, 0)
			if not small and self.flag_options['flag_opacity'] < 1:
				canvas.context.paint_with_alpha(self.flag_options['flag_opacity'])
			else:
				canvas.context.paint()

		self.surface = None


class Border:
	def __init__(self, id:str, d:str, *, _print_progress=True):
		self.print_progress = _print_progress
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
		self.min_x = self.max_x = self.vertices[0][0]
		self.min_y = self.max_y = self.vertices[0][1]
		v_gen = (v for i,v in enumerate(self.vertices) if i%2 == 0)
		for v in v_gen:
			if v is not None:
				self.min_x = min(self.min_x, v[0]); self.max_x = max(self.max_x, v[0])
				self.min_y = min(self.min_y, v[1]); self.max_y = max(self.max_y, v[1])
		self.width = self.max_x - self.min_x
		self.height = self.max_y - self.min_y

	def get_center(self, small_flag_position_lerp:float = 0):
		center_x, center_y = (self.min_x + self.max_x)/2, (self.min_y + self.max_y)/2

		if small_flag_position_lerp > 0:
			try:
				polys = [[]]
				for i, v in enumerate(self.vertices):
					if i % 2 == 0:
						polys[-1].append(v)
					elif v is None:
						polys.append([])
				best_point = None
				best_radius = 0
				for poly in polys:
					if len(poly) >= 3:
						poly_obj = Polygon(poly)
						point = polylabel(poly_obj)
						radius = point.distance(poly_obj.exterior)
						if radius > best_radius:
							best_point = point
							best_radius = radius
				center_x = small_flag_position_lerp*best_point.x + (1 - small_flag_position_lerp)*center_x
				center_y = small_flag_position_lerp*best_point.y + (1 - small_flag_position_lerp)*center_y
			except:
				print(f'Error getting POI for outline of {self.id}:')
				traceback.print_exc()

		return (center_x, center_y)


class ImageMap:
	def __init__(self, map_path:str, epsilon:float = 5, rel_epsilon:float = 1/3,
	             name_function:ty.Optional[ty.Callable[[str],str]] = None):
		self.map_path = map_path
		self.epsilon = epsilon
		self.rel_epsilon = rel_epsilon
		self.name_function = name_function
		self.map, self.map_width, self.map_height = _read_map(map_path)
		self._canvas = cairopath.Canvas(round(self.map_width), round(self.map_height))

	def list(self, output_path:str):
		with open(output_path, 'w', encoding='UTF-8') as f:
			f.write('<imagemap>\n')
			f.write('File:{}|{}px|thumb|right\n'.format(os.path.basename(self.map_path), round(self.map_height)))
			for child in self.map.iter(xmlns + 'path'):
				id = child.attrib['id'] if 'id' in child.attrib else None
				if id:
					name = self.name_function(id) if self.name_function else id
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
		if (self.epsilon or self.rel_epsilon) and len(poly) > 2:
			# Simplify using RDP
			if self.rel_epsilon:
				# Limit epsilon to fraction of polygon width and height
				(min_x, min_y), (max_x, max_y) = poly[0], poly[0]
				for p in poly:
					min_x, min_y = min(min_x, p[0]), min(min_y, p[1])
					max_x, max_y = max(max_x, p[0]), max(max_y, p[1])
				epsilon = max(1, min([self.epsilon, (max_x-min_x)*self.rel_epsilon, (max_y-min_y)*self.rel_epsilon]))
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
