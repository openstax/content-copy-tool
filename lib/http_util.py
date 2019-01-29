import urllib2
import urllib
import httplib
from base64 import b64encode
from tempfile import mkstemp
from os import close

import requests
import signal
import subprocess

from util import CCTError

import makemultipart as multi

"""
This file contains some utility functions for the content-copy-tool that relate
to http requests.
"""

timeout = 300

def http_post_request(url, headers={}, auth=(), data={}):
    """
    Sends a POST request to the specified url with the specified headers, data,
    and authentication tuple. Because we want to the post request to be successful
    in the widest variety of cases, all permanent redirects are treated as a 308
    would (i.e. POST is not converted to GET). Because we expect successful POSTs
    to redirect to the result of the request, temporary redirects are all treated
    as a 303 would (i.e. POST can be converted to GET) and then the following GET
    request redirects are followed.
    """

    MAX_REDIRECTS = 4
    redirects = 0

    def handle_timeout(signal, frame):
        app = '"Terminal"'
        msg = '"Request: %s is taking an exceptionally long time, you might want to skip this task (Ctrl+z)"' % url
        bashCommand = "echo; osascript -e 'tell application "+app+"' -e 'activate' -e 'display alert "+msg+"' -e 'end tell'"
        subprocess.call([bashCommand], shell=True)

    def follow_with_post(response):
        return requests.post(response.headers['Location'], headers=headers, auth=auth, data=data, allow_redirects=False)

    def follow_with_get(response):
        return requests.Session().send(response.next, allow_redirects=False)

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(timeout)
    response = requests.post(url, headers=headers, auth=auth, data=data, allow_redirects=False)
    while response.is_redirect and redirects < MAX_REDIRECTS:
        redirects += 1
        response = {
            True: follow_with_post,
            False: follow_with_get
        }[response.is_permanent_redirect and response.request.method == 'POST'](response)
    if response.is_redirect:
        raise CCTError("POST redirection failed after maximum number of requests")
    signal.alarm(0)
    return response

def http_get_request(url, headers={}, auth=(), data={}):
    """
    Sends a GET request to the specified url with the specified headers, data,
    and authentication tuple.
    """
    def handle_timeout(signal, frame):
        app = '"Terminal"'
        msg = '"Request: %s is taking an exceptionally long time, you might want to skip this task (Ctrl+z)"' % url
        bashCommand = "echo; osascript -e 'tell application "+app+"' -e 'activate' -e 'display alert "+msg+"' -e 'end tell'"
        subprocess.call([bashCommand], shell=True)

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(timeout)
    response = requests.get(url, headers=headers, auth=auth, data=data)
    signal.alarm(0)
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
    def handle_timeout(signal, frame):
        app = '"Terminal"'
        msg = '"Download: %s is taking an exceptionally long time, you might want to skip this task (Ctrl+z)"' % url
        bashCommand = "echo; osascript -e 'tell application "+app+"' -e 'activate' -e 'display alert "+msg+"' -e 'end tell'"
        subprocess.call([bashCommand], shell=True)

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(timeout)
    try:
        urllib.urlretrieve(url, filename + extension)
    except Exception as e:
        print(e)
    signal.alarm(0)
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
    headers = {"Content-Type": "multipart/related;boundary=%s;type=application/atom + xml" % boundary_code,
               "In-Progress": "true", "Accept-Encoding": "zip", "Authorization": 'Basic %s' % userAndPass}
    req = urllib2.Request(url)

    def handle_timeout(signal, frame):
        app = '"Terminal"'
        msg = '"Request: %s is taking an exceptionally long time, you might want to skip this task (Ctrl+z)"' % url
        bashCommand = "echo; osascript -e 'tell application "+app+"' -e 'activate' -e 'display alert "+msg+"' -e 'end tell'"
        subprocess.call([bashCommand], shell=True)

    signal.signal(signal.SIGALRM, handle_timeout)
    signal.alarm(timeout)
    if url.startswith('https://'):
        connection = httplib.HTTPSConnection(req.get_host())
    else:
        connection = httplib.HTTPConnection(req.get_host())
    connection.request('POST', req.get_selector(), open(abs_path), headers)
    response = connection.getresponse()
    signal.alarm(0)
    close(fh)
    return response, abs_path, url

def verify(response, logger):
    """ Returns True if the response code is < 400, False otherwise. """
    if response.status_code < 400:
        return True
    else:
        error = "Failed response: %s %s when sending to %s with data %s" % \
                (response.status_code, response.reason, response.request.url, response.request.body)
        if logger is None:
            print error
        else:
            logger.debug(error)
        return False
