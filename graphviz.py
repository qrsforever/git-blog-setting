#!/usr/bin/python3

"""
Pandoc filter to process code blocks with class "graph" into
graphviz-generated images.
Requires pygraphviz, pandocfilters
"""

import os
import sys

import pygraphviz

from pandocfilters import toJSONFilter, Para, Image, get_filename4code
from pandocfilters import get_caption, get_extension, get_value

dir_name = 'graph'
loc_path = 'source/assets'
git_path = 'https://raw.githubusercontent.com/qrsforever/assets_blog_post/master/'

def graphviz(key, value, format, meta):
    if key == 'CodeBlock':
        [[ident, classes, keyvals], code] = value
        if "graph" in classes:
            caption, typef, keyvals = get_caption(keyvals)
            prog, keyvals = get_value(keyvals, u"prog", u"dot")
            filetype = get_extension(format, "svg", html="svg", latex="pdf")
            dest = get_filename4code(dir_name, code, filetype)
            if not os.path.isfile(dest):
                prefix = ''
                try:
                    datapath = meta['datapath']['c']
                    prefix = datapath[datapath.find('_posts')+7:datapath.find('.md')]
                    localpath = os.path.join(loc_path, prefix, dest)
                    remotepath = os.path.join(git_path, prefix, dest)
                    dir = os.path.dirname(localpath)
                    if not os.path.isdir(dir):
                        os.makedirs(dir)
                except Exception as e:
                    sys.stderr.write('{}: not found datapath in meta, please patch/run.sh\n'.format(e))
                    exit(-1)

                g = pygraphviz.AGraph(string=code)
                g.layout()
                g.draw(localpath, prog=prog)
                sys.stderr.write('Local Path [' + localpath + ']\n')
                sys.stderr.write('Remote Path [' + remotepath + ']\n')

            image = Image([ident, classes, keyvals], 
                          caption, 
                          [remotepath, typef])

            return Para([image])

if __name__ == "__main__":

    toJSONFilter(graphviz)
