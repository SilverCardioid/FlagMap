# Adapted from https://github.com/mwkling/rectangle-overlap (Mike Kling, MIT license)
import itertools
import math
import csv


# This strategy finds all overlaps for all rectangles, then computes a vector for each rectangle
# in the opposite direction of all it overlaps, normalizes and translates by that distance
class Separation:
	def __init__(self, rectangles):
		self.rectangles = rectangles

	def translate_vector(self, idx):
		rect = self.rectangles[idx]
		overlap_vectors = [rect.center_vec(r) for i, r in enumerate(self.rectangles) if i != idx and rect.overlap(r)]

		if len(overlap_vectors) == 0:
			return (0, 0)
		else:
			# This adds up vectors from each overlap if there were multiple
			return list(map(sum, zip(*overlap_vectors)))

	def normalize(self, pair):
		mag = math.sqrt(pair[0]**2 + pair[1]**2)
		if mag == 0:
			return pair
		else:
			return (pair[0] / mag, pair[1] / mag)

	def step(self):
		vecs = [self.normalize(self.translate_vector(i)) for i in range(len(self.rectangles))]
		for i, r in enumerate(self.rectangles):
			r.left += vecs[i][0]
			r.top += vecs[i][1]


class Rectangle:
	def __init__(self, left, top, width, height):
		self.left   = round(left)
		self.top	= round(top)
		self.width  = round(width)
		self.height = round(height)

		# So we can track how far the rectangle moved from original position
		self.original_left = self.left
		self.original_top  = self.top

	@property
	def right(self):
		return self.left + self.width

	@property
	def bottom(self):
		return self.top + self.height

	@property
	def area(self):
		return self.width * self.height

	@property
	def original_right(self):
		return self.original_left + self.width

	@property
	def original_bottom(self):
		return self.original_top + self.height

	@property
	def midx(self):
		return (self.left + self.right) / 2

	@property
	def midy(self):
		return (self.top + self.bottom) / 2

	@property
	def original_midx(self):
		return (self.original_left + self.original_right) / 2

	@property
	def original_midy(self):
		return (self.original_top + self.original_bottom) / 2

	@property
	def distance_from_original(self):
		return math.sqrt((self.left - self.original_left) ** 2 + (self.top - self.original_top) ** 2)

	@property
	def deltax(self):
		return self.original_left - self.left

	@property
	def deltay(self):
		return self.original_top - self.top

	def rotate(self, theta):
		# Note: important not to assign directly to self.left here first, as that would then mess
		# up calculation of the value for self.top
		new_left = self.original_left + self.deltax * math.cos(theta) - self.deltay * math.sin(theta)
		new_top  = self.original_top + self.deltax * math.sin(theta) + self.deltay * math.cos(theta)

		self.left = new_left
		self.top  = new_top

	def overlap(self, other):
		if(self.left >= other.right or other.left >= self.right):
			return False
		if(self.top >= other.bottom or other.top >= self.bottom):
			return False
		return True

	def overlapx(self, other):
		return max(0, min(self.right, other.right) - max(self.left, other.left))

	def overlapy(self, other):
		return max(0, min(self.bottom, other.bottom) - max(self.top, other.top))

	def overlap_rect(self, other):
		left = max(self.left, other.left)
		top = max(self.top, other.top)
		return Rectangle(left, top, self.overlapx(other), self.overlapy(other))

	def center_vec(self, other):
		return (self.midx - other.midx, self.midy - other.midy)

	def as_tuple(self):
		return (self.left, self.top, self.width, self.height)

	def __str__(self):
		return "Rect" + str(self.as_tuple())

	@staticmethod
	def has_overlaps(rectangles):
		for (r1, r2) in itertools.combinations(rectangles, 2):
			if r1.overlap(r2):
				return True
		return False

	@staticmethod
	def overlap_rectangles(rectangles):
		return [r1.overlap_rect(r2) for r1, r2 in itertools.combinations(rectangles, 2) if r1.overlap(r2)]

	@staticmethod
	def total_movement(rectangles):
		return sum([r.distance_from_original for r in rectangles])

	@staticmethod
	def to_csv(rectangles, out):
		with open(out, 'w') as f:
			writer = csv.writer(f)
			writer.writerows([r.as_tuple() for r in rectangles])

	@staticmethod
	def from_csv(csvfile):
		rects = []
		with open(csvfile, 'r') as f:
			reader = csv.reader(f)
			for (left, top, width, height) in reader:
				rects.append(Rectangle(left, top, width, height))
		return rects
