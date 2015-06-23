import urllib2
import urllib
import httplib
from base64 import b64encode
from tempfile import mkstemp
from os import close

import requests

import makemultipart as multi

"""
This file contains some utility functions for the content-copy-tool that relate
to http requests.
"""

def http_post_request(url, headers={}, auth=(), data={}):
    """
    Sends a POST request to the specified url with the specified headers, data,
    and authentication tuple.
    """
    response = requests.post(url, headers=headers, auth=auth, data=data)
    return response

def http_get_request(url, headers={}, auth=(), data={}):
    """
    Sends a GET request to the specified url with the specified headers, data,
    and authentication tuple.
    """
    response = requests.get(url, headers=headers, auth=auth, data=data)
    return response

def http_request(url, headers={}, data={}):
    """
    Sends an HTTP request to the specified url with the specified headers and
    data. If no data is provided, the request will be a GET, if data is provided
    the request will be a POST.
    """
    request = urllib2.Request(url)
    if headers:
        for key, value in headers.iteritems():
            request.add_header(key, value)
    if data:
        request.add_data(urllib.urlencode(data))
    try:
        response = urllib2.urlopen(request)
        return response
    except urllib2.HTTPError, e:
        print e.message

def http_download_file(url, filename, extension):
    """ Downloads the file at [url] and saves it as [filename.extension]. """
    try:
        urllib.urlretrieve(url, filename + extension)
    except urllib.error.URLError as e:
        print(e.reason)
    return filename + extension

def extract_boundary(filename):
    """ Extracts the boundary line of a multipart file at filename. """
    boundary_start = 'boundary=\"'
    boundary_end = '\"'
    with open(filename) as file:
        text = file.read()
        start = text.find(boundary_start) + len(boundary_start)
        end = text.find(boundary_end, start)
        return text[start:end]

def http_upload_file(xmlfile, zipfile, url, credentials, mpartfilename='tmp'):
    """
    Uploads a multipart file made up of the given xml and zip files to the
    given url with the given credentials. The temporary multipartfile can be
    named with the mpartfilename parameter.
    """
    fh, abs_path = mkstemp('.mpart', mpartfilename)
    multi.makemultipart(open(xmlfile), open(zipfile), open(abs_path, 'w'))
    boundary_code = extract_boundary(abs_path)
    userAndPass = b64encode(credentials).decode("ascii")
    headers = {"Content-Type": "multipart/related;boundary=" + boundary_code + ";type=application/atom + xml",
               "In-Progress": "true", "Accept-Encoding": "zip", "Authorization": 'Basic %s' % userAndPass}
    req = urllib2.Request(url)
    connection = httplib.HTTPConnection(req.get_host())
    connection.request('POST', req.get_selector(), open(abs_path), headers)
    response = connection.getresponse()
    close(fh)
    return response, abs_path

def verify(response):
    """ Returns True if the response code is < 400, False otherwise. """
    if response.status_code < 400:
        return True
    else:
        print response.status_code, response.reason
        return False
