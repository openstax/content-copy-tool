import urllib2
import urllib
import httplib
import requests
import makemultipart as multi
import re
from base64 import b64encode
from tempfile import mkstemp
from os import close

def http_post_request(url, headers={}, auth=(), data={}):
    # print "POST to: "+url
    # print data
    response = requests.post(url, headers=headers, auth=auth, data=data)
    return response#.status

def http_request(url, headers={}, data={}):
    print url
    request = urllib2.Request(url)
    if headers:
        for key, value in headers.iteritems():
            request.add_header(key, value)
    if data:
        request.add_data(urllib.urlencode(data))
    try:
        response = urllib2.urlopen(request)
        print response.getcode()
        return response
    except urllib2.HTTPError, e:
        print e.message

def http_download_file(url, filename, extension):
    fh, abs_path = mkstemp(extension, filename)
    # r = requests.get(url, stream=True)
    try: urllib.urlretrieve(url, filename+extension)
    except urllib.error.URLError as e:
        print(e.reason)
    close(fh)
    return abs_path

def extract_boundary(filename):
    boundary_start = 'boundary=\"'
    boundary_end = '\"'
    with open(filename) as file:
        text = file.read()
        start = text.find(boundary_start)+len(boundary_start)
        end = text.find(boundary_end, start)
        return text[start:end]

def http_upload_file(xmlfile, zipfile, url, credentials, mpartfilename='tmp'):
    fh, abs_path = mkstemp('.mpart', mpartfilename)
    multi.makemultipart(open(xmlfile), open(zipfile), open(abs_path, 'w'))
    boundary_code = extract_boundary(abs_path)
    userAndPass = b64encode(credentials).decode("ascii")
    headers = {"Content-Type": "multipart/related;boundary="+boundary_code+";type=application/atom+xml", "In-Progress": "true", "Accept-Encoding":"zip", "Authorization" : 'Basic %s' %  userAndPass }
    req = urllib2.Request(url)
    connection = httplib.HTTPConnection(req.get_host())
    connection.request('POST', req.get_selector(), open(abs_path), headers)
    response = connection.getresponse()
    close(fh)
    return response, abs_path
    # print response.status, response.reason

def verify(response):
    # print response.status_code
    if response.status_code < 400:
        return True
    else:
        print response.status_code, response.reason
        return False

# http_download_file('http://legacy.cnx.org/content/m10672/latest/module_export?format=zip', 'example.zip')
# http_download_file('http://legacy.cnx.org/content/m10672/latest/rhaptos-deposit-receipt', 'example.xml')
# http_upload_file('example.xml', 'example.zip', 'http://legacydev.cnx.org/GroupWorkspaces/wg2965/m53456/sword', 'user2:user2')
