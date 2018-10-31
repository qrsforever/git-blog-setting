#!/bin/bash

# npm install hexo-renderer-mathjax
# npm install hexo-renderer-kramed
# npm install kramed

cp ./renderer.js ../node_modules/hexo-renderer-kramed/lib/renderer.js
cp ./mathjax.html ../node_modules/hexo-renderer-mathjax/mathjax.html
cp ./inline.js ../node_modules/kramed/lib/rules/inline.js
