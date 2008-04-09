#!/usr/bin/env python
"""Embed userView data into png file.

Usage: viewEmbed.py userViews.xml
$Id$
"""
import sys, os

if len(sys.argv) != 2:
    sys.exit(__doc__)

from xml.dom import minidom
import pngFile

xmldoc = minidom.parse(sys.argv[1])
for view in xmldoc.getElementsByTagName("userView"):
    fname = view.getAttribute('name') + '.png'
    if os.path.exists(fname):
        stat = os.stat(fname)
        outfile = open(fname + '2', 'wb') # temporary file
        # outfile = tempfile.NamedTemporaryFile()
        outfile.write(pngFile.pngSignature)
        for chunk in pngFile.readChunks(open(fname, 'rb')):
            if chunk.startswith('tEXt'):
                key, value = chunk[4:].split('\0', 1)
                if key == 'userView':
                    continue # discard old view data
            elif chunk.startswith('IEND'):
                # Insert view just before end
                outfile.write(pngFile.encodeChunk('tEXtuserView\0' +
                    str(view.toxml())))
            # copy chunk to outfile
            outfile.write(pngFile.encodeChunk(chunk))
        print fname
        outfile.close()
        os.utime(outfile.name, (stat.st_atime, stat.st_mtime))
        os.remove(fname)
        os.rename(outfile.name, fname)
