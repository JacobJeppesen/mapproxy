# This file is part of the MapProxy project.
# Copyright (C) 2011 Omniscale <http://omniscale.de>
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
HTTP client that directly calls CGI executable.
"""

import os
import subprocess
import errno

from mapproxy.source import SourceError
from mapproxy.image import ImageSource
from mapproxy.client.http import HTTPClientError
from StringIO import StringIO
from urlparse import urlparse


def split_http_response(data):
    headers = []
    prev_n = 0
    while True:
        next_n = data.find('\n', prev_n)
        if next_n < 0:
            break 
        next_line_begin = data[next_n+1:next_n+3]
        headers.append(data[prev_n:next_n].rstrip('\r'))
        if next_line_begin[0] == '\n':
            return headers_dict(headers), data[next_n+2:]
        elif next_line_begin == '\r\n':
            return headers_dict(headers), data[next_n+3:]
        prev_n = next_n+1
    return {}, data

def headers_dict(header_lines):
    headers = {}
    for line in header_lines:
        if ':' in line:
            key, value = line.split(':', 1)
            value = value.strip()
        else:
            key = line
            value = None
        key = key[0].upper() + key[1:].lower()
        headers[key] = value
    return headers

class CGIClient(object):
    def __init__(self, script, no_headers=False, working_directory=None):
        self.script = script
        self.working_directory = working_directory
        self.no_headers = no_headers
    
    def open(self, url, data=None):
        assert data is None, 'POST requests not supported by CGIClient'
        
        parsed_url = urlparse(url)
        environ = {
            'QUERY_STRING': parsed_url.query,
        }
        
        try:
            p = subprocess.Popen([self.script], env=environ,
                stdout=subprocess.PIPE,
                cwd=self.working_directory or os.path.dirname(self.script)
            )
        except OSError, ex:
            if ex.errno == errno.ENOENT:
                raise SourceError('CGI script not found (%s)' % (self.script,))
            elif ex.errno == errno.EACCES:
                raise SourceError('No permission for CGI script (%s)' % (self.script,))
            else:
                raise
            
        stdout = p.communicate()[0]
        ret = p.wait()
        if ret != 0:
            raise HTTPClientError('Error during CGI call (exit code: %d)' 
                                              % (ret, ))
        
        if self.no_headers:
            content = stdout
            headers = dict()
        else:
            headers, content = split_http_response(stdout)
        
        content = StringIO(content)
        content.headers = headers
        return content
    
    def open_image(self, url, data=None):
        resp = self.open(url, data=data)
        if 'Content-type' in resp.headers:
            if not resp.headers['Content-type'].lower().startswith('image'):
                raise HTTPClientError('response is not an image: (%s)' % (resp.read()))
        return ImageSource(resp)

