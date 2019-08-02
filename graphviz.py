#!/usr/bin/python3

"""
Pandoc filter to process code blocks with class "graph" into
graphviz-generated images.
Requires pygraphviz, pandocfilters
"""

import os
import sys
import hashlib

import pygraphviz

from pandocfilters import toJSONFilter, Para, Image
from pandocfilters import get_caption, get_extension, get_value

tmp_path = '/tmp/gitblog'
top_path = os.path.abspath(os.path.dirname(__file__))
dir_name = 'graph-image'
git_path = 'https://raw.githubusercontent.com/qrsforever/assets_blog_post/master/'
git_post = '?sanitize=true'

doc_tmpl = r"""\documentclass[12pt,border=5pt,varwidth=true]{standalone}
\usepackage{graphicx}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{psfrag}
\begin{document}
    \input{%s}
    \includegraphics{%s}
\end{document} """

def graphviz(key, value, format, meta):
    if key == 'CodeBlock':
        [[ident, classes, keyvals], code] = value
        if "graph" in classes:
            caption, typef, keyvals = get_caption(keyvals)
            prog, keyvals = get_value(keyvals, u"prog", u"dot")
            filetype = get_extension(format, "svg", html="svg", latex="pdf")
            md5 = hashlib.sha1(code.encode(sys.getfilesystemencoding())).hexdigest()
            basename, _ = get_value(keyvals, u"fileName")
            if basename is None:
                sys.stderr.write('not set filename in {}\n')
                exit(-1)

            latex, _ = get_value(keyvals, u"latex")
            if latex is not None:
                filetype = 'png'

            filename = basename + '.' + filetype
            while True:
                try:
                    datapath = meta['datapath']['c']
                    drafts_idx = datapath.find('_drafts')
                    if drafts_idx > 0:
                        prefix = datapath[drafts_idx+8:-3]
                    else:
                        prefix = datapath[datapath.find('_posts')+7:-3]
                    filepath = os.path.join(prefix, dir_name, filename)
                    if drafts_idx > 0:
                        localpath = os.path.join(top_path, "source/assets", filepath)
                        remotepath = os.path.join("/assets", filepath)
                    else:
                        localpath = os.path.join(top_path, "source/_assets", filepath)
                        remotepath = os.path.join(git_path, filepath) + git_post
                    if os.path.exists(localpath):
                        if os.path.exists(localpath + '.' + md5):
                            break
                        else:
                            os.system('rm -f %s*' % localpath)

                    dir = os.path.dirname(localpath)
                    if not os.path.isdir(dir):
                        os.makedirs(dir)

                    if latex is None:
                        g = pygraphviz.AGraph(string=code)
                        g.layout()
                        g.draw(localpath, prog=prog)
                    else:
                        ladot_file = os.path.join(tmp_path, '{}.ladot'.format(basename))
                        latex_file = os.path.join(tmp_path, '{}.latex'.format(basename))

                        with open(ladot_file, 'w') as f:
                            f.write(code)

                        with open(latex_file, 'w') as f:
                            f.write(doc_tmpl % ('{}.tex'.format(basename), '{}.ps'.format(basename)))

                        resolution, _ = get_value(keyvals, u"resolution")
                        if resolution is None:
                            resolution = "1200"
                        density, _ = get_value(keyvals, u"density")
                        if density is None:
                            density = "200"

                        # sys.stderr.write('{}/ladot {} {} {} {}'.format(top_path, ladot_file, tmp_path, resolution, density))
                        os.system('{}/ladot {} {} {} {}'.format(top_path, ladot_file, tmp_path, resolution, density))
                        if os.path.exists('%s.png' % os.path.join(tmp_path, basename)):
                            os.system('cp %s.png %s' % (os.path.join(tmp_path, basename), localpath))

                    sys.stderr.write('Local Path [' + localpath + ']\n')
                    sys.stderr.write('Remote Path [' + remotepath + ']\n')
                    os.system('touch %s.%s' % (localpath, md5))
                except Exception as e:
                    sys.stderr.write('{}: not found datapath in meta, please patch/run.sh\n'.format(e))
                    exit(-1)
                finally:
                    break

            image = Image([ident, classes, keyvals],
                          caption,
                          [remotepath, typef])

            return Para([image])

if __name__ == "__main__":
    if not os.path.exists(tmp_path):
        os.mkdir(tmp_path)
    toJSONFilter(graphviz)
