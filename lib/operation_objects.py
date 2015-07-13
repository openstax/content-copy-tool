from shutil import rmtree
from os import remove, path, walk
import re as regex
import zipfile
import http_util as http
from role_updates import RoleUpdater
from util import CCTError
from bookmap import Collection

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
    def __init__(self, modules, workgroups, copy, roles, accept_roles, collections, units,
                 publish, publish_collection, chapters, exclude, dryrun):
        self.modules = modules
        self.workgroups = workgroups
        if self.workgroups:
            self.modules = True
        self.copy = copy
        self.roles = roles
        self.accept_roles = accept_roles
        self.collections = collections
        self.units = units
        self.publish = publish
        self.publish_collection = publish_collection
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

    def clean_zip(self, zipfilename):
        """ Removes the index.cnxml.html file if it is in the given zipfile. """
        zipfileobject = zipfile.ZipFile(zipfilename, 'r')
        for filename in zipfileobject.namelist():
            if regex.search(r'.*/index.cnxml.html', filename):
                dir = self.extract_zip(zipfilename)
                remove(zipfilename)
                zipdir = self.path_to_tool + '/' + dir
                self.remove_file_from_dir(zipdir, 'index.cnxml.html')
                self.zipdir(zipdir, zipfilename)
                break

    def copy_content(self, role_config, run_options, logger, failures):
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
            if module.valid and module.chapter_number in run_options.chapters:
                files = []
                if module.source_id is None:
                    logger.error("Module " + module.title + " has no source id")
                    failures.append((module.full_title(), ": module has not source id"))
                    continue
                logger.info("Copying content for module: " + str(module.source_id) + " - " + module.full_title())
                if not run_options.dryrun:
                    files.append(http.http_download_file(self.config.source_server + '/content/' + module.source_id +
                                                         '/latest/module_export?format=zip', module.source_id, '.zip'))
                    files.append(http.http_download_file(self.config.source_server + '/content/' + module.source_id +
                                                         '/latest/rhaptos-deposit-receipt', module.source_id, '.xml'))
                    try:
                        if run_options.roles:
                            RoleUpdater(role_config).run_update_roles(module.source_id + '.xml')
                    except CCTError:
                        logger.error("Failure updating roles on module " + module.source_id)
                        module.valid = False
                        failures.append((module.full_title(), " updating roles"))

                    try:
                        self.clean_zip(module.source_id + '.zip')  # remove index.cnxml.html from zipfile
                    except Exception, e:
                        logger.debug("Error: " + str(e))
                        logger.error("Failed cleaning module zipfile " + module.title)
                        module.valid = False
                        failures.append((module.full_title(), " cleaning module zipfile "))
                        continue

                    res, mpart = http.http_upload_file(module.source_id + '.xml', module.source_id + '.zip',
                                                       module.destination_workspace_url + "/" + module.destination_id +
                                                       '/sword', self.config.credentials)
                    files.append(mpart)
                    # clean up temp files
                    if res.status < 400:
                        for temp_file in files:
                            remove(temp_file)
                    else:
                        logger.error("Failed copying module " + module.title)
                        module.valid = False
                        failures.append((module.full_title(), " copying module "))

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
            self.create_workgroup(workgroup, server, credentials, logger)

    def create_workgroup(self, workgroup, server, credentials, logger):
        """
        Creates a workgroup with [title] on [server] with [credentials] using
        HTTP requests.

        Returns:
          None

        Modifies:
          The workgroup provided is updated with the new found information: id and url
        """
        username, password = credentials.split(':')
        data = {"title": workgroup.title, "form.button.Reference": "Create", "form.submitted": "1"}
        response = http.http_post_request(server + '/create_workgroup', auth=(username, password), data=data)
        if not http.verify(response, logger):
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
        if workgroup_url != 'Members/':
            info_str += " in workgroup: " + workgroup_url
        else:
            workgroup_url += credentials.split(':')[0]
            workgroup_url = server + '/' + workgroup_url
            info_str += " in Personal workspace (" + workgroup_url + ")"
        logger.info(info_str)
        if not dryrun:
            temp_url = self.create_module(module.title, credentials, workgroup_url, logger)
            res, url = self.publish_module(temp_url, credentials, logger)
            module.destination_workspace_url = workgroup_url
            module.destination_id = res

    def create_module(self, title, credentials, workspace_url, logger):
        """
        Creates a module with [title] in [workspace_url] with [credentials].

        Returns the url of the created module.

        Raises CustomError on failed http requests.
        """
        username, password = credentials.split(':')
        auth = username, password

        data1 = {"type_name": "Module",
                 "workspace_factories:method": "Create New Item"}

        response1 = http.http_post_request(workspace_url, auth=auth, data=data1)
        if not http.verify(response1, logger):
            raise CCTError('create module for' + title + ' request 1 failed: ' + str(response1.status_code) + ' ' +
                           response1.reason)
        cc_license = self.get_license(response1)
        data2 = {"agree": "on",
                 "form.button.next": "Next >>",
                 "license": cc_license,
                 "form.submitted": "1"}
        data3 = {"title": title,
                 "master_language": "en",
                 "language": "en",
                 "license": cc_license,
                 "form.button.next": "Next >>",
                 "form.submitted": "1"}
        response2 = http.http_post_request(response1.url.encode('UTF-8'), auth=auth, data=data2)
        if not http.verify(response2, logger):
            raise CCTError('create module for ' + title + ' request 2 failed: ' + str(response2.status_code) + ' ' +
                           response2.reason)
        r2url = response2.url.encode('UTF-8')
        create_url = r2url[:regex.search('cc_license', r2url).start()]
        response3 = http.http_post_request(create_url + 'content_title', auth=auth, data=data3)
        if not http.verify(response3, logger):
            raise CCTError('create module for ' + title + ' request 3 failed: ' + str(response3.status_code) + ' ' +
                           response3.reason)
        return create_url

    def publish_module(self, module_url, credentials, logger, new=True):
        """
        Publishes the module at [module_url] with [credentials] using HTTP requests.

        Returns the published module ID.
        Raises a CustomError on http request failure.
        """
        username, password = credentials.split(':')
        data1 = {"message": "created module", "form.button.publish": "Publish", "form.submitted": "1"}
        response1 = http.http_post_request(module_url + 'module_publish_description', auth=(username, password),
                                           data=data1)
        if not http.verify(response1, logger):
            raise CCTError('publish module for ' + module_url + ' request 1 failed: ' + str(response1.status_code) + ' '
                           + response1.reason)
        if new:
            data2 = {"message": "created module", "publish": "Yes, Publish"}
            response2 = http.http_post_request(module_url + 'publishContent', auth=(username, password), data=data2)
            if not http.verify(response2, logger):
                raise CCTError('publish module for ' + module_url + ' request 2 failed: ' + str(response1.status_code) +
                               ' ' + response1.reason)

            # extract module ID
            url = response2.url.encode('UTF-8')
            end_id = regex.search('/content_published', url).start()
            beg = url.rfind('/', 0, end_id) + 1
            return url[beg:end_id], url
        else:
            return module_url[module_url.rfind('/', 0, -1) + 1:-1], module_url

    def get_license(self, response):
        html = str(response.text)
        start = regex.search(r'<input\s*type="hidden"\s*name="license"\s*value="', html)
        return html[start.end():html.find('"', start.end())]

    def create_collection(self, credentials, title, server, logger):
        logger.info("Creating collection " + title)
        auth = tuple(credentials.split(':'))
        data0 = {"type_name": "Collection",
                 "workspace_factories:method": "Create New Item"}
        response0 = http.http_post_request(server + "/Members/" + auth[0], auth=auth, data=data0)
        if not http.verify(response0, logger):
            raise CCTError('Creation of collection ' + title + ' request 2 failed: ' + str(response0.status_code) +
                           ' ' + response0.reason)
        cc_license = self.get_license(response0)
        data1 = {"agree": "on",
                 "form.button.next": "Next >>",
                 "license": cc_license,
                 "type_name": "Collection",
                 "form.submitted": "1"}
        data2 = {"title": title,
                 "master_language": "en",
                 "language": "en",
                 "collectionType": "",
                 "keywords:lines": "",
                 "abstract": "",
                 "license": cc_license,
                 "form.button.next": "Next >>",
                 "form.submitted": "1"}
        response1 = http.http_post_request(response0.url, auth=auth, data=data1)
        if not http.verify(response1, None):
            raise CCTError('Creation of collection ' + title + ' request 2 failed: ' + str(response1.status_code) +
                           ' ' + response1.reason)
        url = response1.url
        base = url[:url.rfind('/')+1]
        response2 = http.http_post_request(base + '/content_title', auth=auth, data=data2)
        if not http.verify(response2, None):
            raise CCTError('Creation of collection ' + title + ' request 3 failed: ' + str(response2.status_code) +
                           ' ' + response2.reason)
        start = base[:-1].rfind('/')+1
        return Collection(title, str(base[start:-1]))

    def add_subcollections(self, titles, server, credentials, collection, logger):
        logger.info("Adding subcollections to collection " + collection.title + ": " + str(titles))
        auth = tuple(credentials.split(':'))
        base = server + "/Members/" + auth[0] + "/" + collection.get_parents_url() + "/"
        data4 = {"form.submitted": "1",
                 "titles": "\n".join(titles),
                 "submit": "Add new subcollections"}
        subcollection = '@@collection-composer-collection-subcollection'
        response = http.http_post_request(base + subcollection, auth=auth, data=data4)
        if not http.verify(response, logger):
            raise CCTError('Creation of subcollection(s) ' + str(titles) + ' request failed: ' +
                           str(response.status_code) + ' ' + response.reason)
        text = response.text[len("close:["):-1]
        text = text.split("},{")
        subcollections = []
        for subcollection_response in text:
            subcollection_id_start = regex.search(r'nodeid\':\'', subcollection_response).end()
            subcollection_id = subcollection_response[subcollection_id_start:
                                                      subcollection_response.find("'", subcollection_id_start)]
            subcollection_title_start = regex.search(r'text\':\s*\'', subcollection_response).end()
            subcollection_title = subcollection_response[subcollection_title_start:
                                                         subcollection_response.find("'", subcollection_title_start)]
            subcollection = Collection(subcollection_title, subcollection_id)
            subcollection.parent = collection
            collection.add_member(subcollection)
            subcollections.append(subcollection)
        return subcollections

    def add_modules_to_collection(self, modules, server, credentials, collection, logger, failures):
        modules_str = ""
        for module in modules:
            modules_str += module.destination_id + " "
        logger.info("Adding modules to collection " + collection.title + ": " + modules_str)
        auth = tuple(credentials.split(':'))
        data = {"form.submitted": "1",
                "form.action": "submit"}
        collection_url = collection.get_parents_url()
        for module in modules:
            if not module.valid:
                continue
            data["ids:list"] = module.destination_id
            response = http.http_post_request(server + "/Members/" + auth[0] + "/" + collection_url +
                                              "/" + "@@collection-composer-collection-module", auth=auth, data=data)
            if not http.verify(response, logger):
                logger.error("Module " + module.title + " failed to be added to collection " + collection.title)
                module.valid = False
                failures.append((module.full_title, " adding to collection"))
                continue

    def publish_collection(self, server, credentials, collection, logger):
        logger.info("Publishing collection " + collection.title)
        auth = tuple(credentials.split(':'))
        publish_message = "Initial publish"
        data1 = {"message": publish_message,
                 "form.button.publish": "Publish",
                 "form.submitted": "1"}
        response1 = http.http_post_request(server + "/Members/" + auth[0] + "/" + collection.id + "/collection_publish",
                                           auth=auth, data=data1)
        if not http.verify(response1, logger):
            raise CCTError('Publishing collection ' + collection.title + ' request 1 failed: ' +
                           str(response1.status_code) + ' ' + response1.reason)
        data2 = {"message": publish_message,
                 "publish": "Yes, Publish"}
        response2 = http.http_post_request(server + "/Members/" + auth[0] + "/" + collection.id + "/publishContent",
                                           auth=auth, data=data2)
        if not http.verify(response2, logger):
            raise CCTError('Publishing collection ' + collection.title + ' request 2 failed: ' +
                           str(response2.status_code) + ' ' + response2.reason)
        # response2.
