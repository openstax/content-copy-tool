import requests
import re
import http_util as http

def run_create_workgroup(title, server, credentials, logger, dryrun=False):
    """
    Uses HTTP requests to create a workgroup with the given information

    Arguments:
      title       - the title of the workgroup
      server      - the server to create the workgroup on
      credentials - the username:password to use when creating the workgroup
      dryrun      - (optional) a flag to step through the setup and teardown
                    without actually creating the workgroup

    Returns:
      the ID of the created workgroup, 'wg00000' if dryrun, 'FAIL' on failure
    """
    logger.info("Creating workgroup: " + title + " on " + server)
    res = 'wg00000'
    if not dryrun:
        res = create_workgroup(title, server, credentials)
    return res

def create_workgroup(title, server, credentials):
    username, password = credentials.split(':')
    data = {"title": title, "form.button.Referece": "Create", "form.submitted": "1"}
    response = http.http_post_request(server+'/create_workgroup', auth=(username, password), data=data)
    if not http.verify(response):
        return 'FAIL'

    # extract workgroup ID
    url = response.url.encode('UTF-8')
    id_start = re.search('GroupWorkspaces/', url).end()
    workgroup_id = url[id_start:url.find('/', id_start)]
    return workgroup_id

def run_create_and_publish_module(title, server, credentials, logger, workgroup_url='Members/', dryrun=False):
    """
    Uses HTTP requests to create and publish a module with the given information

    Arguments:
      title         - the title of the module
      server        - the server to create the module on
      credentials   - the username:password to use when creating the module
      workgroup_url - (optional) the workgroup to create the module in,
                      will create it outside of workgroups if not specified
      dryrun        - (optional) a flag to step through the setup and
                      teardown without actually creating the module

    Returns:
      the ID of the created module, 'm00000' if dryrun, 'FAIL' on failure
    """
    info_str = "Creating module: "+title+" on "+server
    if workgroup_url is not 'Members/':
        info_str += " in workgroup: "+ workgroup_url
    else:
        workgroup_url += credentials.split(':')[0]
        workgroup_url = server+'/'+workspace_url
        info_str += " in Personal workspace ("+workgroup_url+")"
    logger.info(info_str)
    res = 'm00000'
    if not dryrun:
        module_url = create_module(title, credentials, workgroup_url)
        if module_url == 1:
            return 'FAIL'
        res = publish_module(module_url, credentials)
    return res

def create_module(title, credentials, workspace_url):
    username, password = credentials.split(':')
    auth = username, password

    data1 = {"type_name":"Module", "workspace_factories:method":"Create New Item"}
    data2 = {"agree":"on", "form.button.next":"Next >>", "license":"http://creativecommons.org/licenses/by/4.0/", "form.submitted":"1"}
    data3 = {"title":title, "master_lanuage":"en", "language":"en", "license":"http://creativecommons.org/licenses/by/4.0/", "form.button.next":"Next >>", "form.submitted":"1"}

    response1 = http.http_post_request(workspace_url, auth=auth, data=data1)
    if not http.verify(response1):
        return 1
    response2 = http.http_post_request(response1.url.encode('UTF-8'), auth=auth, data=data2)
    if not http.verify(response2):
        return 1
    r2url = response2.url.encode('UTF-8')
    create_url = r2url[:re.search('cc_license', r2url).start()]
    response3 = http.http_post_request(create_url + 'content_title', auth=auth, data=data3)
    if not http.verify(response3):
        return 1
    return create_url

def publish_module(module_url, credentials):
    username, password = credentials.split(':')
    data1 = {"message":"created module", "form.button.publish":"Publish", "form.submitted":"1"}
    response1 = http.http_post_request(module_url+'module_publish_description', auth=(username, password), data=data1)
    if not http.verify(response1):
        return 'FAIL'
    data2 = {"message":"created module", "publish":"Yes, Publish"}
    response2 = http.http_post_request(module_url+'publishContent', auth=(username, password), data=data2)
    if not http.verify(response2):
        return 'FAIL'

    # extract module ID
    url = response2.url.encode('UTF-8')
    end_id=re.search('/content_published',url).start()
    beg = url.rfind('/',0,end_id)+1
    return url[beg:end_id]

    # print response2.text
    # response = http.http_post_request(module_url, \
    #     headers={'In-Progress': 'False'}, auth=(username, password), data={"message":"created module"})



# data={"type_name":"Module", "workspace_factories:method":"Create New Item"}
# response1 = requests.post('http://legacydev.cnx.org/GroupWorkspaces/wg2974/', auth=auth, data=data)
# data2 = {"agree":"on", "form.button.next":"Next >>", "license":"http://creativecommons.org/licenses/by/4.0/", "form.submitted":"1"}
# response2 = requests.post(response1.url.encode('UTF-8'), auth=auth, data=data2)
# data3 = {"title":"test-module-6-4-again-again", "master_lanuage":"en", "language":"en", "license":"http://creativecommons.org/licenses/by/4.0/", "form.button.next":"Next >>", "form.submitted":"1"}
# r2url = response2.url.encode('UTF-8')
# r2url = r2url[:re.search('cc_license', r2url).start()]
# response3 = requests.post(r2url + 'content_title', auth=auth, data=data3)
