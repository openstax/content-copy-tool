from shutil import rmtree
from os import remove, path, walk
import re as regex
import zipfile
import http_util as http
from role_updates import RoleUpdater
from util import CCTError

"""
This file contains the Copy and Content Creation related objects
"""
# Configuration Objects
class CopyConfiguration:
    """ The configuration data that the copier requires. """
    def __init__(self, source_server, destination_server, credentials):
        self.source_server = source_server
        self.destination_server = destination_server
        self.credentials = credentials


class RunOptions:
    """ The input options that describe what the tool will do. """
    def __init__(self, modules, workgroups, copy, roles, accept_roles, publish, chapters, exclude, dryrun):
        self.modules = modules
        self.workgroups = workgroups
        if self.workgroups:
            self.modules = True
        self.copy = copy
        self.roles = roles
        self.accept_roles = accept_roles
        self.publish = publish
        self.chapters = chapters
        self.exclude = exclude
        self.dryrun = dryrun


# Operation Objects
class Copier:
    """ The object that does the copying from one server to another. """
    def __init__(self, config, copy_map, path_to_tool):
        self.config = config
        self.copy_map = copy_map
        self.path_to_tool = path_to_tool

    def extract_zip(self, zipfilepath):
        """ Extracts the data from the given zip file. """
        with zipfile.ZipFile(zipfilepath, "r") as zipf:
            temp_item = zipf.namelist()[0]
            new_dir = temp_item[:temp_item.find('/')]
            zipf.extractall()
        return new_dir

    def remove_file_from_dir(self, directory, filename):
        """ Removes the given file from the given directory. """
        remove(directory + '/' + filename)

    def zipdir(self, file_path, zipfilename):
        """ Zips the given directory into a zip file with the given name. """
        zipf = zipfile.ZipFile(zipfilename, 'w')
        for root, dirs, files in walk(file_path):
            for file_in_dir in files:
                zipf.write(path.join(root, file_in_dir))
        zipf.close()
        rmtree(file_path)

    def clean_zip(self, zipfile):
        """ Removes the index.cnxml.html file if it is in the given zipfile. """
        if 'index.cnxml.html' in zipfile.ZipFile(zipfilename, 'r').name_list():
            dir = self.extract_zip(zipfile)
            remove(zipfile)
            zipdir = self.path_to_tool + '/' + dir
            self.remove_file_from_dir(zipdir, 'index.cnxml.html')
            self.zipdir(zipdir, zipfile)

    def copy_content(self, role_config, run_options, logger):
        """
        Copies content from source server to server specified by each entry in the
        content copy map.

        Arguments:
          role_config - the configuration with the role update information
          run_options - the input running options that tell the tool what to do on this run
          logger      - a reference to the tool's logger

        Returns:
          Nothing. It will, however, leave temporary & downloaded files for content
          that did not succeed in transfer.
        """
        for module in self.copy_map.modules:
            if module.chapter_number in run_options.chapters:
                files = []
                if module.source_id is None:
                    raise CCTError("Module [" + module.title + "]has not source id")
                logger.info("Copying content for module: " + str(module.source_id))
                if not run_options.dryrun:
                    files.append(http.http_download_file(self.config.source_server + '/content/' + module.source_id +
                                                         '/latest/module_export?format=zip', module.source_id, '.zip'))
                    files.append(http.http_download_file(self.config.source_server + '/content/' + module.source_id +
                                                         '/latest/rhaptos-deposit-receipt', module.source_id, '.xml'))
                    if run_options.roles:
                        RoleUpdater(role_config).run_update_roles(module.source_id + '.xml')

                    self.clean_zip(module.source_id + '.zip')  # remove index.cnxml.html from zipfile

                    res, mpart = http.http_upload_file(module.source_id + '.xml', module.source_id + '.zip',
                                                       module.destination_workspace_url + "/" + module.destination_id +
                                                       '/sword', self.config.credentials)
                    files.append(mpart)
                    # clean up temp files
                    if res.status < 400:
                        for temp_file in files:
                            remove(temp_file)
                    else:
                        raise CCTError("Failure to copy module " + str(module.source_id))

class ContentCreator:
    def __init__(self, server, credentials):
        self.server = server
        self.credentials = credentials

    def run_create_workgroup(self, workgroup, server, credentials, logger, dryrun=False):
        """
        Uses HTTP requests to create a workgroup with the given information

        Arguments:
          title       - the title of the workgroup
          server      - the server to create the workgroup on
          credentials - the username:password to use when creating the workgroup
          dryrun      - (optional) a flag to step through the setup and teardown
                        without actually creating the workgroup

        Returns:
          the ID of the created workgroup object, id='wg00000' if dryrun
        """
        logger.info("Creating workgroup: " + workgroup.title + " on " + server)
        if not dryrun:
            try:
                self.create_workgroup(workgroup, server, credentials)
            except CCTError, error:
                print error.msg

    def create_workgroup(self, workgroup, server, credentials):
        """
        TODO update docstring
        Creates a workgroup with [title] on [server] with [credentials] using
        HTTP requests.

        Returns:
          the created workgroup object, FAIL on failure.
        """
        username, password = credentials.split(':')
        data = {"title": workgroup.title, "form.button.Reference": "Create", "form.submitted": "1"}
        response = http.http_post_request(server + '/create_workgroup', auth=(username, password), data=data)
        if not http.verify(response):
            raise CCTError(str(response.status_code) + ' ' + response.reason)

        # extract workgroup ID
        url = response.url.encode('UTF-8')
        id_start = regex.search('GroupWorkspaces/', url).end()
        id_end = url.find('/', id_start)
        workgroup.id = url[id_start:id_end]
        workgroup.url = url[:id_end]

    def run_create_and_publish_module(self, module, server, credentials, logger, workgroup_url='Members/',
                                      dryrun=False):
        """
        Uses HTTP requests to create and publish a module with the given information

        Arguments:
          module        - the module object to create a publish
          server        - the server to create the module on
          credentials   - the username:password to use when creating the module
          workgroup_url - (optional) the workgroup to create the module in,
                          will create it outside of workgroups if not specified
          dryrun        - (optional) a flag to step through the setup and
                          teardown without actually creating the module

        Returns:
            None

        Modifies:
            The given module is added the destination_workspace_url and destination_module_id
        """
        info_str = "Creating module: " + module.title + " on " + server
        if workgroup_url is not 'Members/':
            info_str += " in workgroup: " + workgroup_url
        else:
            workgroup_url += credentials.split(':')[0]
            workgroup_url = server + '/' + workgroup_url
            info_str += " in Personal workspace (" + workgroup_url + ")"
        logger.info(info_str)
        if not dryrun:
            temp_url = self.create_module(module.title, credentials, workgroup_url)
            res, url = self.publish_module(temp_url, credentials)
            module.destination_workspace_url = workgroup_url
            module.destination_id = res

    def create_module(self, title, credentials, workspace_url):
        """
        Creates a module with [title] in [workspace_url] with [credentials].

        Returns the url of the created module.

        Raises CustomError on failed http requests.
        """
        username, password = credentials.split(':')
        auth = username, password

        data1 = {"type_name": "Module",
                 "workspace_factories:method": "Create New Item"}
        data2 = {"agree": "on",
                 "form.button.next": "Next >>",
                 "license": "http://creativecommons.org/licenses/by/4.0/",
                 "form.submitted": "1"}
        data3 = {"title": title,
                 "master_language": "en",
                 "language": "en",
                 "license": "http://creativecommons.org/licenses/by/4.0/",
                 "form.button.next": "Next >>",
                 "form.submitted": "1"}

        response1 = http.http_post_request(workspace_url, auth=auth, data=data1)
        if not http.verify(response1):
            raise CCTError('create module for' + title + ' request 1 failed: ' + response1.status_code + ' ' +
                              response1.reason)
        response2 = http.http_post_request(response1.url.encode('UTF-8'), auth=auth, data=data2)
        if not http.verify(response2):
            raise CCTError('create module for ' + title + ' request 2 failed: ' + response2.status_code + ' ' +
                              response2.reason)
        r2url = response2.url.encode('UTF-8')
        create_url = r2url[:regex.search('cc_license', r2url).start()]
        response3 = http.http_post_request(create_url + 'content_title', auth=auth, data=data3)
        if not http.verify(response3):
            raise CCTError('create module for ' + title + ' request 3 failed: ' + response3.status_code + ' ' +
                              response3.reason)
        return create_url

    def publish_module(self, module_url, credentials, new=True):
        """
        Publishes the module at [module_url] with [credentials] using HTTP requests.

        Returns the published module ID.
        Raises a CustomError on http request failure.
        """
        username, password = credentials.split(':')
        data1 = {"message": "created module", "form.button.publish": "Publish", "form.submitted": "1"}
        response1 = http.http_post_request(module_url + 'module_publish_description', auth=(username, password),
                                           data=data1)
        if not http.verify(response1):
            raise CCTError('publish module for ' + module_url + ' request 1 failed: ' + response1.status_code + ' ' +
                              response1.reason)
        if new:
            data2 = {"message": "created module", "publish": "Yes, Publish"}
            response2 = http.http_post_request(module_url + 'publishContent', auth=(username, password), data=data2)
            if not http.verify(response2):
                raise CCTError('publish module for ' + module_url + ' request 2 failed: ' + response1.status_code +
                                  ' ' + response1.reason)

            # extract module ID
            url = response2.url.encode('UTF-8')
            end_id = regex.search('/content_published', url).start()
            beg = url.rfind('/', 0, end_id) + 1
            return url[beg:end_id], url
        else:
            return module_url[module_url.rfind('/', 0, -1) + 1:-1], module_url
