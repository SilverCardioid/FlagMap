""" Download a set of flags from Wikimedia Commons """

import os
import time
import typing as ty
import urllib.parse
import urllib.request

def download(fileMap:ty.Dict[str, str], targetFolder:str):
	""" Download a set of flags into targetFolder.
	fileMap is a dict mapping region IDs (target filenames without extension) to Commons filenames. """
	if not os.path.exists(targetFolder):
		os.mkdir(targetFolder)

	for code, file in fileMap.items():
		url = 'https://commons.wikimedia.org/wiki/Special:FilePath/' + urllib.parse.quote(file.replace(' ','_'))
		targetName = code + os.path.splitext(file)[1]
		target = os.path.join(targetFolder, targetName)
		urllib.request.urlretrieve(url, target)
		print(f'Downloaded {file} as {targetName}')
		time.sleep(0.5)
