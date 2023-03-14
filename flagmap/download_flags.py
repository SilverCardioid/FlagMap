""" Download a set of flags from Wikimedia Commons """

import os
import time
import typing as ty
import urllib.parse
import urllib.request

def download_file(filename:str, path:ty.Optional[str] = None):
	"""Download the Commons file with the given filename to a local path."""
	url = 'https://commons.wikimedia.org/wiki/Special:FilePath/' + urllib.parse.quote(filename.replace(' ','_'))
	urllib.request.urlretrieve(url, path)

def download(file_map:ty.Mapping[str, str], folder:str):
	"""Download a set of Commons files into a local folder.
	file_map is a mapping from region IDs (target filenames without extension) to Commons filenames.
	"""
	if not os.path.exists(folder):
		os.mkdir(folder)

	for code, file in file_map.items():
		target_name = code + os.path.splitext(file)[1]
		target_path = os.path.join(folder, target_name)
		download_file(file, target_path)
		print(f'Downloaded {file} as {target_name}')
		time.sleep(0.5)
