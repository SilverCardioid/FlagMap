""" Download and resize the US state flags """

import sys
sys.path.insert(0, '..')
from helpers import download_flags, resize_flags

# Dictionary mapping region codes (corresponding to IDs in the base map) to Commons filenames
usFlags = {
	"AK": "File:Flag of Alaska.svg",
	"AL": "File:Flag of Alabama.svg",
	"AR": "File:Flag of Arkansas.svg",
	"AZ": "File:Flag of Arizona.svg",
	"CA": "File:Flag of California.svg",
	"CO": "File:Flag of Colorado.svg",
	"CT": "File:Flag of Connecticut.svg",
	"DC": "File:Flag of the District of Columbia.svg",
	"DE": "File:Flag of Delaware.svg",
	"FL": "File:Flag of Florida.svg",
	"GA": "File:Flag of Georgia (U.S. state).svg",
	"HI": "File:Flag of Hawaii.svg",
	"IA": "File:Flag of Iowa.svg",
	"ID": "File:Flag of Idaho.svg",
	"IL": "File:Flag of Illinois.svg",
	"IN": "File:Flag of Indiana.svg",
	"KS": "File:Flag of Kansas.svg",
	"KY": "File:Flag of Kentucky.svg",
	"LA": "File:Flag of Louisiana.svg",
	"MA": "File:Flag of Massachusetts.svg",
	"MD": "File:Flag of Maryland.svg",
	"ME": "File:Flag of Maine.svg",
	"MI": "File:Flag of Michigan.svg",
	"MN": "File:Flag of Minnesota.svg",
	"MO": "File:Flag of Missouri.svg",
	"MS": "File:Flag of Mississippi (\"New Magnolia Flag\").svg",
	"MT": "File:Flag of Montana.svg",
	"NC": "File:Flag of North Carolina.svg",
	"ND": "File:Flag of North Dakota.svg",
	"NE": "File:Flag of Nebraska.svg",
	"NH": "File:Flag of New Hampshire.svg",
	"NJ": "File:Flag of New Jersey.svg",
	"NM": "File:Flag of New Mexico.svg",
	"NV": "File:Flag of Nevada.svg",
	"NY": "File:Flag of New York.svg",
	"OH": "File:Flag of Ohio.svg",
	"OK": "File:Flag of Oklahoma.svg",
	"OR": "File:Flag of Oregon.svg",
	"PA": "File:Flag of Pennsylvania.svg",
	"RI": "File:Flag of Rhode Island.svg",
	"SC": "File:Flag of South Carolina.svg",
	"SD": "File:Flag of South Dakota.svg",
	"TN": "File:Flag of Tennessee.svg",
	"TX": "File:Flag of Texas.svg",
	#"UT": "File:Flag of Utah.svg", # simpler rendition of the flag (faster)
	"UT": "File:Flag of the State of Utah.svg", # more elaborate version
	"VA": "File:Flag of Virginia.svg",
	"VT": "File:Flag of Vermont.svg",
	"WA": "File:Flag of Washington.svg",
	"WI": "File:Flag of Wisconsin.svg",
	"WV": "File:Flag of West Virginia.svg",
	"WY": "File:Flag of Wyoming.svg"
}

download_flags.download(usFlags, 'US')
resize_flags.resize_folder('US')
