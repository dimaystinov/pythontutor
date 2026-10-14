# Local browser dependencies

Vendored from official npm package tarballs (no runtime CDN dependency):

- jquery 3.7.1: `npm pack jquery@3.7.1`, dist/jquery.min.js; MIT, jquery-LICENSE.txt.
- bootstrap 3.4.1: `npm pack bootstrap@3.4.1`, dist/; MIT, bootstrap-LICENSE.txt.
- mathjax 3.2.2: `npm pack mathjax@3.2.2`, es5/tex-svg.js; Apache-2.0, mathjax/LICENSE.

MathJax uses bundled SVG fonts, with dynamic TeX autoload/require and the optional menu disabled to remain offline. ACE and jsPlumb are retained from the archive to preserve visualizer behavior; their license headers remain in source.
