""" Edit SVG files in a folder to limit their dimensions to a given value """

import os
import re
import tempfile
import traceback

# Very much reinventing the wheel by parsing SVGs this way, but the built-in xml library
# doesn't seem to offer a way to edit just the root element and write out the result
# without parsing all child nodes or changing formatting/attribute orders.
WIDTH = re.compile(r'(?<=\s)width\s*=\s*(["\'])(?P<value>.+?)(?P<unit>[cm]m|in|p[ctx]|e[mx]|%)?\1')
HEIGHT = re.compile(r'(?<=\s)height\s*=\s*(["\'])(?P<value>.+?)(?P<unit>[cm]m|in|p[ctx]|e[mx]|%)?\1')
VIEWBOX = re.compile(r'(?<=\s)viewBox\s*=\s*(["\'])(?P<value>.+?)\1')
BUFFER_SIZE = 1000

def resize_file(path:str, *, maxSize:float = 600):
	""" Resize an SVG file so that it is no more than `maxSize` pixels wide or high. """
	fileName = os.path.basename(path)
	with tempfile.TemporaryFile('w+', encoding='UTF-8') as tf:
		# Copy the file's contents
		with open(path, 'r', encoding='UTF-8') as f:
			while True:
				buffer = f.read(BUFFER_SIZE)
				if not buffer: break # EOF
				tf.write(buffer)
		tf.seek(0)

		# Extract root SVG tag
		head = ''
		while '<svg' not in head:
			buffer = tf.read(BUFFER_SIZE)
			if not buffer: break # EOF
			head += buffer
		tagStart = head.index('<svg')
		head, svg = head[:tagStart], head[tagStart:]

		while '>' not in svg:
			buffer = tf.read(BUFFER_SIZE)
			if not buffer: break # EOF
			svg += buffer
		tagEnd = svg.index('>')
		svg, buffer = svg[:tagEnd+1], svg[tagEnd+1:]

		# Find and change dimensions
		width = re.search(WIDTH, svg)
		height = re.search(HEIGHT, svg)
		viewbox = re.search(VIEWBOX, svg)
		if not width or not height:
			print(f'File with no width or height attribute ignored: {fileName}')
			return False
		if width['unit'] != height['unit']:
			print(f'File with different units for width and height ignored: {fileName}')
			return False
		unit = width['unit'] or ''

		w = float(width['value'])
		h = float(height['value'])
		scale = maxSize / max(w, h)
		if scale >= 1 and not unit:
			# Smaller than given limit: don't change
			return False

		addVB = ''
		if not viewbox:
			addVB = f' viewBox="0 0 {w:g} {h:g}"'
		svg = svg.replace(width[0],  f'width="{scale*w:g}"')
		svg = svg.replace(height[0], f'height="{scale*h:g}"{addVB}')

		# Write to the original file
		with open(path, 'w', encoding='UTF-8') as f:
			f.write(head)
			f.write(svg)
			f.write(buffer)
			while True:
				buffer = tf.read(BUFFER_SIZE)
				if not buffer: break # EOF
				f.write(buffer)
		print(f'{fileName} resized: {w:g}x{h:g}{unit} -> {scale*w:g}x{scale*h:g}')
		return True

def resize_folder(folderName:str, *, maxSize:float = 600):
	""" Resize all SVG files in a folder so that they are no more than `maxSize` pixels wide or high. """
	files = os.listdir(folderName)
	files.sort()
	for file in files:
		if os.path.splitext(file)[1] != '.svg':
			continue
		filePath = os.path.join(folderName, file)
		try:
			resize_file(filePath, maxSize=maxSize)
		except:
			print(f'Error while parsing {file}:')
			traceback.print_exc()
