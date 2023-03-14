import sys
#sys.path.insert(0, '..')
import flagmap

mapOptions = {
	'height': 1200,
	'background_color': '#444',
	'stroke_color': '#aaa',
	'stroke_width': 1.5,
	'preserve_aspect_ratio': True,
	'flag_opacity': 1,
	'small_flag': False
}

# Load base map and add flags
map = flagmap.FlagMap('US_map.svg', mapOptions)
map.add_folder('US')

# Add key points (areas of the flag to focus on when cropping)
map.flags['GA'].flag_options['key_point'] = (5/24, 1/3)
map.flags['NV'].flag_options['key_point'] = (16/75, 16/50)
map.flags['OH'].flag_options['key_point'] = (10/52, 1/2)
# Add custom flag outline shape
map.flags['OH'].flag_options['outline'] = [(0, 0), (1, 6/32), (40/52, 1/2), (1, 26/32), (0, 1)]

# Draw flag map
map.draw('US_flagmap.png')

# Draw map with small flags
for flag in map.flags.values():
	flag.flag_options['small_flag'] = True
map.draw('US_flagmap_small.png')
