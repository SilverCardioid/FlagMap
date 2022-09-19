import sys
sys.path.insert(0, '..')
import flagmap

mapOptions = {
	'height': 1200,
	'backgroundColor': '#444',
	'strokeColor': '#aaa',
	'strokeWidth': 1.5,
	'preserveAspectRatio': True,
	'flagOpacity': 1,
	'smallFlag': False
}

# Load base map and add flags
map = flagmap.FlagMap('US_map.svg', mapOptions)
map.addFlagsFromFolder('US')

# Add key points (areas of the flag to focus on when cropping)
map.flags['GA'].flagOptions['keyPoint'] = (5/24, 1/3)
map.flags['NV'].flagOptions['keyPoint'] = (16/75, 16/50)
map.flags['OH'].flagOptions['keyPoint'] = (10/52, 1/2)
# Add custom flag outline shape
map.flags['OH'].flagOptions['outline'] = [(0, 0), (1, 6/32), (40/52, 1/2), (1, 26/32), (0, 1)]

# Draw flag map
map.draw('US_flagmap.png')

# Draw map with small flags
for flag in map.flags.values():
	flag.flagOptions['smallFlag'] = True
map.draw('US_flagmap_small.png')
