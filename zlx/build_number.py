from __future__ import absolute_import
import io
import re
import zlx.io

def _replace (match):
    return '{}{}'.format(match.group(1), int(match.group(2)) + 1)

def inc (source = None, path = None, pattern = 'BUILD =', save_path = None):
    if source is None and path is not None:
        with open(path, 'r') as f: source = f.read()
    if isinstance(pattern, str):
        pattern = re.compile(r'({}\s*)(\d+)'.format(pattern))
    out = io.StringIO()
    for line in source.splitlines():
        out.write(pattern.sub(_replace, line) + u'\n')
    content = out.getvalue()
    if save_path:
        with open(save_path, 'w') as f: f.write(content)
    return content

