# flagmap
A Python module for creating flag maps. This includes maps with flags filling the region borders ("map flags"), as well as normal maps overlaid with small flag images ("small flags"), or both. It can also create corresponding [image maps](https://www.mediawiki.org/wiki/Extension:ImageMap) for MediaWiki wikis.

| Map flags | Small flags |
| --------- | ----------- |
| ![](/examples/US_flagmap.png) | ![](/examples/US_flagmap_small.png) |

## Installation
Requirements:
* [cairocffi](https://github.com/Kozea/cairocffi) (needs a Cairo DLL; see [here](https://github.com/SilverCardioid/CairoSVG#requirements) for more information)
* [cairopath](https://github.com/SilverCardioid/cairopath)
* [CairoSVG](https://github.com/Kozea/CairoSVG)
* [rdp](https://pypi.org/project/rdp/)
* [shapely](https://pypi.org/project/Shapely/)

A version of the [rectangle-overlap](https://github.com/mwkling/rectangle-overlap) repository is included in this library as the helper module `flagmap.separate`.

Installation using Pip (includes all requirements except the Cairo DLL):
```
pip install git+https://github.com/SilverCardioid/FlagMap.git
```

## Usage
A flag map requires flags in .svg or .png format, and a map in .svg format. Each region in the map should be a single path with an `id` attribute, which is used for matching flags with regions. Only the path coordinates are used when reading the map file; attributes such as styling and transforms are disregarded.

## Reference

### FlagMap class
```python
map = flagmap.FlagMap(map_path:str, options:dict = {}, *, print_progress:bool = True):
```

Possible map options:
* `height`: height in pixels of the output map (defaults to the input map size)
* `background_color` (default `#444`): map background fill colour
* `map_color` (`#ddd`): map region fill colour
* `stroke_color` (`#aaa`): map region stroke colour, and default small flag outline colour
* `stroke_width` (1): map region stroke width, and default small flag outline width
* `flag_opacity` (1): opacity for map flags
* `preserve_aspect_ratio` (True): if False, stretch map flags to fit the regions' bounding boxes
* `small_flag` (False): draw small flags instead of map flags by default
* `small_flag_size`: size for small flags (in px along the diagonal; default: height/40)
* `small_flag_threshold` (None): set a size threshold for regions (px diagonal) below which flags are drawn as small flags
* `small_flag_separate` (True): run an algorithm to avoid small flags overlapping
* `small_flag_spacing`: minimum distance between small flags after separating (in px; default: `small_flag_size/5`)
* `small_flag_position_lerp` (0.5): set the method for calculating the default position of small flags:
    * 0 for the centre of the region's bounding box (which may or may not lie inside the region)
    * 1 for the [pole of inaccessibility](https://en.wikipedia.org/wiki/Pole_of_inaccessibility), i.e. the centre of the largest inscribed circle
    * a different value for a linear interpolation of the two

The options are stored as the `map.map_options` property. `stroke_color`, `stroke_width`, `flag_opacity`, `small_flag` and `small_flag_size` are passed through to [`Flag`](#flag-class) objects as default values for their `flag_options` when flags are added; later changes to `map_options` don't affect `flag_options`.

Flags are added through the FlagMap's `add_flags` and `add_folder` methods, and stored in `map.flags` as a dictionary mapping region IDs to `Flag` objects. A separate property `map.small_flags` is used when `small=True` in these methods, which is useful for maps with both kinds of flags on the same region. Flags in `map.flags` may still be drawn as small flags based on their `small_flag` value and the `small_flag_threshold` option.

#### add_flags
```python
map.add_flags(flags:Dict[str, str], flag_options:dict = {}, *, small:bool = False, overwrite:bool = True) -> FlagMap
```
Add flags to the flag map. `flags` is a dictionary mapping region IDs to filenames. See [below](#flag-class) for possible flag options. `overwrite` determines whether to replace or ignore existing IDs. `small=True` can be used instead of the `small_flag` option to avoid overriding map flags with the same ID (see [above](#flagmap-class)).

#### add_folder
```python
map.add_folder(folder:str, flag_options:dict = {}, *, small:bool = False, overwrite:bool = False, recursive:bool = False) -> FlagMap
```
Add all SVG and PNG files from a directory to the map (with SVGs having precedence over PNGs). For each file, the filename without the extension is used as the ID. If `recursive=True`, also add files from subdirectories. The other arguments are the same as `add_flags`.

#### draw
```python
map.draw(output_path:str)
```
Draw and export the flag map.

### Flag class
```python
flag = flagmap.Flag(id:str, file_path:str, options:dict = {}):
```
Created internally by the map's `add_flags` methods.

Possible flag options (which, unless otherwise noted, default to the corresponding `map_options` value):
* 'stroke_color': small flag outline colour
* 'stroke_width': small flag outline width
* 'flag_opacity': opacity for map flags
* 'small_flag': draw small flags instead of map flags
* 'small_flag_size': size for small flags
* 'key_point': point of interest of the flag in fractions of its width and height; used to ensure an important section of a map flag (such as [Nevada](https://en.wikipedia.org/wiki/Flag_of_Nevada)'s top-left emblem) is visible after cropping to the region's aspect ratio (default `(0.5, 0.5)`, i.e. the centre)
* 'outline': the shape used for the flag outline, as a list of `(x,y)` points in fractions of the flag's width and height (default `[(0,0), (1,0), (1,1), (0,1)]`, i.e. a rectangle)

### ImageMap class
```python
im = flagmap.ImageMap(map_path:str, epsilon:Optional[float] = 5, rel_epsilon:Optional[float] = 1/3, name_function:Optional[Callable] = None):
im.list(output_path:str)
```
Generate and export the wikicode for an [image map](https://www.mediawiki.org/wiki/Extension:ImageMap) based on an SVG map image.

Region borders are simplified with the [Ramer–Douglas–Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm) (RDP). The `epsilon` parameter sets the size threshold for this operation in pixels (the maximum deviation from the original shape). `rel_epsilon` sets an additional threshold as a fraction of the region's size, to avoid overly distorting very small regions. Set both to `None` to use the original region shapes without applying RDP.

`name_function` is an optional callable that should map a region ID (its input parameter) to the pagename to link the region to. If not provided, the IDs themselves are used as the link names.

## Known issues
* When a flag image has a large intrinsic size and needs to be scaled down too much for the flag map, Cairo renders it pixelated, or not at all. A workaround is to edit such flags externally to reduce their dimensions. `flagmap.resize_flags` is a utility module for this, which is used in the example script `US_download.py`.

## Feature ideas & todos
* SVG output
* Display region names on the map
* Carry over colours and other styling from the input map
* A simple GUI to match flags with regions, and to customise flag placement
* Refactor to be more intuitive in how to change options after initialisation
