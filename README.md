# flagmap
A Python module for creating flag maps. This includes maps with flags filling the region borders ("map flags"), as well as normal maps overlaid with small flag images ("small flags"), or both. It can also create corresponding [image maps](https://www.mediawiki.org/wiki/Extension:ImageMap) for MediaWiki wikis.

| Map flags | Small flags |
| --------- | ----------- |
| ![](/examples/US_flagmap.png) | ![](/examples/US_flagmap_small.png) |

## Requirements
* [cairocffi](https://github.com/Kozea/cairocffi) (needs a Cairo DLL; see [here](https://github.com/SilverCardioid/CairoSVG#requirements) for more information)
* [cairopath](https://github.com/SilverCardioid/cairopath)
* [CairoSVG](https://github.com/Kozea/CairoSVG)
* [rdp](https://pypi.org/project/rdp/)
* [shapely](https://pypi.org/project/Shapely/)

A version of the [rectangle-overlap](https://github.com/mwkling/rectangle-overlap) repository is included in this library as the `separate` helper module.

## Usage
A flag map requires flags in .svg or .png format, and a map in .svg format. Each region in the map should be a single path with an `id` attribute, which is used for matching flags with regions. Only the path coordinates are used when reading the map file; attributes such as styling and transforms are disregarded.

## Reference

### FlagMap class
```python
map = FlagMap(mapPath:str, mapOptions:dict = {}, *, printProgress:bool = True):
```

Possible map options:
* `height`: height in pixels of the output map (defaults to the input map size)
* `backgroundColor` (default `#444`): map background fill colour
* `mapColor` (`#ddd`): map region fill colour
* `strokeColor` (`#aaa`): map region stroke colour, and default small flag outline colour
* `strokeWidth` (1): map region stroke width, and default small flag outline width
* `flagOpacity` (1): opacity for map flags
* `preserveAspectRatio` (True): if False, stretch map flags to fit the regions' bounding boxes
* `smallFlag` (False): draw small flags instead of map flags by default
* `smallFlagSize`: size for small flags (in px along the diagonal; default: height/40)
* `smallFlagThreshold` (None): set a size threshold for regions (px diagonal) below which flags are drawn as small flags
* `smallFlagSeparate` (True): run an algorithm to avoid small flags overlapping
* `smallFlagSpacing`: minimum distance between small flags after separating (in px; default: smallFlagSize/5)
* `lerpPOI` (0.5): set the method for calculating the default position of small flags:
    * 0 for the centre of the region's bounding box (which may or may not lie inside the region)
    * 1 for the [pole of inaccessibility](https://en.wikipedia.org/wiki/Pole_of_inaccessibility), i.e. the centre of the largest inscribed circle
    * a different value for a linear interpolation of the two

The options are stored as the `map.mapOptions` property. `strokeColor`, `strokeWidth`, `flagOpacity`, `smallFlag` and `smallFlagSize` are passed through to [`Flag`](#flag-class) objects as default values for their `flagOptions` when flags are added; later changes to `mapOptions` don't affect `flagOptions`.

Flags are added through the FlagMap's `addFlags` and `addFlagsFromFolder` methods, and stored in `map.flags` as a dictionary mapping region IDs to `Flag` objects. A separate property `map.smallFlags` is used when `small=True` in these methods, which is useful for maps with both kinds of flags on the same region. Flags in `map.flags` may still be drawn as small flags based on their `smallFlag` value and the `smallFlagThreshold` option.

#### addFlags
```python
map.addFlags(flags:Dict[str, str], flagOptions:dict = {}, *, overwrite:bool = True, small:bool = False) -> FlagMap
```
Add flags to the flag map. `flags` is a dictionary mapping region IDs to filenames. See [below](#flag-class) for possible flag options. `overwrite` determines whether to replace or ignore existing IDs. `small=True` can be used instead of the `smallFlag` option to avoid overriding map flags with the same ID (see [above](#flagmap-class)).

#### addFlagsFromFolder
```python
map.addFlagsFromFolder(folder:str, flagOptions:dict = {}, *, recursive:bool = False, overwrite:bool = False, small:bool = False) -> FlagMap
```
Add all SVG and PNG files from a directory to the map (with SVGs having precedence over PNGs). For each file, the filename without the extension is used as the ID. If `recursive=True`, also add files from subdirectories. The other arguments are the same as `addFlags`.

#### draw
```python
map.draw(outputPath:str)
```
Draw and export the flag map.

### Flag class
```python
flag = Flag(id:str, filePath:str, flagOptions:dict = {}):
```
Created internally by the map's `addFlags` methods.

Possible flag options (which, unless otherwise noted, default to the corresponding `mapOptions` value):
* 'strokeColor': small flag outline colour
* 'strokeWidth': small flag outline width
* 'flagOpacity': opacity for map flags
* 'smallFlag': draw small flags instead of map flags
* 'smallFlagSize': size for small flags
* 'keyPoint': point of interest of the flag in fractions of its width and height; used to ensure an important section of a map flag (such as [Nevada](https://en.wikipedia.org/wiki/Flag_of_Nevada)'s top-left emblem) is visible after cropping to the region's aspect ratio (default `(0.5, 0.5)`, i.e. the centre)
* 'outline': the shape used for the flag outline, as a list of `(x,y)` points in fractions of the flag's width and height (default `[(0,0), (1,0), (1,1), (0,1)]`, i.e. a rectangle)

### ImageMap class
```python
im = ImageMap(mapPath:str, epsilon:Optional[float] = 5, relEpsilon:Optional[float] = 1/3, nameFunction:Optional[Callable] = None):
im.list(outputPath:str)
```
Generate and export the wikicode for an [image map](https://www.mediawiki.org/wiki/Extension:ImageMap) based on an SVG map image.

Region borders are simplified with the [Ramer–Douglas–Peucker algorithm](https://en.wikipedia.org/wiki/Ramer%E2%80%93Douglas%E2%80%93Peucker_algorithm) (RDP). The `epsilon` parameter sets the size threshold for this operation in pixels (the maximum deviation from the original shape). `relEpsilon` sets an additional threshold as a fraction of the region's size, to avoid overly distorting very small regions. Set both to `None` to use the original region shapes without applying RDP.

`nameFunction` is an optional callable that should map a region ID (its input parameter) to the pagename to link the region to. If not provided, the IDs themselves are used as the link names.

## Known issues
* When a flag image has a large intrinsic size and needs to be scaled down too much for the flag map, Cairo renders it pixelated, or not at all. A workaround is to edit such flags externally to reduce their dimensions. `helpers/resize_flags.py` is a utility module for this, which is used in the `download` example script.

## Feature ideas & todos
* Display region names on the map
* Carry over colours and other styling from the input map
* A simple GUI to match flags with regions, and to customise flag placement
* Refactor to be more intuitive in how to change options after initialisation
