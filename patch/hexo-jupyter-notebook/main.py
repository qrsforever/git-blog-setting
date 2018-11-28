"""
jupyter convert
"""

from __future__ import print_function
import sys
import re
from nbconvert import HTMLExporter


def main(asset_dir, jupyter_file):
    """
    convert jupyter file to html
    :params jupyter_file: juptyer file path
    """
    html_exporter = HTMLExporter()
    html_exporter.template_file = 'full'

    # lidong add
    import random
    import os
    num = random.randint(1111, 9999)
    dn = os.path.dirname(asset_dir)
    if os.path.exists(dn + ".md"):
        dn = os.path.dirname(dn)
        jupyter_file = os.path.join(dn, jupyter_file)
    else:
        print("not found: " + os.path.join(asset_dir, jupyter_file))
        return

    restr = "%s" % (str(html_exporter.from_filename(jupyter_file)[0]))
    # lidong mod, jquery only use 2.0.0, other have some problems
    template = """
<script src="http://code.jquery.com/jquery-2.0.0.js"></script>
<iframe id="ipynb-%d" marginheight="0" marginwidth="0" frameborder="0" width="100%%" srcdoc="%s" style="scrolling:no;">
</iframe>
<script>
$("#ipynb-%d").load( function() {
document.getElementById('ipynb-%d').height=$("#ipynb-%d").contents().find("#notebook").height()+100;
})
</script> 
    """ % (num, restr.replace("\"", "'"), num, num, num)
    # print(sys.version)
    # template = '2341'
    print(re.sub(r'<a.*?\/a>', '', template))

main(sys.argv[1], sys.argv[2])