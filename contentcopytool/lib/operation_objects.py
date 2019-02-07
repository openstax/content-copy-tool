from shutil import rmtree
from os import remove, path, walk, getpid
import re as regex
import traceback
import zipfile
import http_util as http
from role_updates import RoleUpdater
from util import CCTError, SkipSignal, TerminateError
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
        remove("%s/%s" % (directory, filename))

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
                zipdir = "%s/%s" % (self.path_to_tool, dir)
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
                if not module.destination_workspace_url or module.destination_workspace_url == "":
                    logger.error("Module %s destination workspace url is invalid: %s" %
                                 (module.title, module.destination_workspace_url))
                    module.valid = False
                    failures.append((module.full_title(), "copying module"))
                    continue
                if not module.destination_id or module.destination_id == "":
                    logger.error("Module %s destination id is invalid: %s" %
                                 (module.title, module.destination_id))
                    module.valid = False
                    failures.append((module.full_title(), "copying module"))
                    continue
                http_server = regex.match(r'https?://', self.config.destination_server)
                http_workgroup = regex.match(r'https?://', module.destination_workspace_url)
                if not http_server or not http_workgroup:
                    logger.error("Either the destination server: %s or "
                                 "the module's destination workgroup url: %s is bad." %
                                 (self.config.destination_server, module.destination_workspace_url))
                    logger.error("Failure copying module %s" % module.source_id)
                    module.valid = False
                    failures.append((module.full_title(), "copying module"))
                    continue
                else:
                    if not regex.search(self.config.destination_server[http_server.end():],
                                        module.destination_workspace_url[http_workgroup.end():]):
                        logger.error("Destination workspace does not match destination server! "
                                     "Destination Server: %s vs. Workspace URL: %s" %
                                     (self.config.destination_server, module.destination_workspace_url))
                        module.valid = False
                        failures.append((module.full_title(), "copying module"))
                        continue
                    try:
                        files = []
                        if module.source_id is None:
                            logger.error("Module %s has no source id" % module.title)
                            module.valid = False
                            failures.append((module.full_title(), ": module has not source id"))
                            continue
                        logger.info("Copying content for module: %s - %s" % (module.source_id, module.full_title()))
                        if not run_options.dryrun:
                            files.append(http.http_download_file("%s/content/%s/latest/module_export?format=zip&nonce=%s" %
                                                                 (self.config.source_server, module.source_id, getpid()),
                                                                 module.source_id, '.zip'))
                            files.append(http.http_download_file("%s/content/%s/latest/rhaptos-deposit-receipt?nonce=%s" %
                                                                 (self.config.source_server, module.source_id, getpid()),
                                                                 module.source_id, '.xml'))
                            try:
                                if run_options.roles:
                                    RoleUpdater(role_config).run_update_roles("%s.xml" % module.source_id)
                            except TerminateError:
                                raise TerminateError("Terminate Signaled")
                            except (CCTError, Exception) as e:
                                if type(e) is not CCTError and type(e) is not SkipSignal:
                                    logger.error("Problematic Error")
                                    logger.debug(traceback.format_exc())
                                if type(e) is SkipSignal:
                                    logger.warn("User skipped creating workgroup.")
                                logger.error("Failure updating roles on module %s" % module.source_id)
                                module.valid = False
                                failures.append((module.full_title(), " updating roles"))
                                continue

                            try:
                                self.clean_zip("%s.zip" % module.source_id)  # remove index.cnxml.html from zipfile
                            except TerminateError:
                                raise TerminateError("Terminate Signaled")
                            except Exception as e:
                                logger.debug(traceback.format_exc())
                                logger.error("Failed cleaning module zipfile %s" % module.title)
                                module.valid = False
                                failures.append((module.full_title(), " cleaning module zipfile "))
                                continue
                            res, mpart, url = http.http_upload_file("%s.xml" % module.source_id,
                                                                    "%s.zip" % module.source_id,
                                                                    "%s/%s/sword" % (module.destination_workspace_url,
                                                                                     module.destination_id),
                                                                    self.config.credentials)
                            files.append(mpart)
                            # clean up temp files
                            if res.status < 400:
                                for temp_file in files:
                                    remove(temp_file)
                            else:
                                logger.error("Failed uploading module %s, response %s %s when sending to %s" %
                                             (module.title, res.status, res.reason, url))
                                module.valid = False
                                failures.append((module.full_title(), " uploading module "))
                    except TerminateError:
                        raise TerminateError("Terminate Signaled")
                    except (CCTError, Exception) as e:
                        if type(e) is not CCTError and type(e) is not SkipSignal:
                            logger.error("Problematic Error")
                            logger.debug(traceback.format_exc())
                        if type(e) is SkipSignal:
                            logger.warn("User skipped copying module.")
                        logger.error("Failure copying module %s" % module.source_id)
                        module.valid = False
                        failures.append((module.full_title(), "copying module"))


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
        logger.info("Creating workgroup: %s on %s" % (workgroup.title, server))
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
        response = http.http_post_request("%s/create_workgroup" % server, auth=(username, password), data=data)
        if not http.verify(response, logger):
            raise CCTError("%s %s" % (response.status_code, response.reason))

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
        info_str = "Creating module: %s on %s" % (module.title, server)
        if workgroup_url != 'Members/':
            info_str += " in workgroup: %s" % workgroup_url
        else:
            workgroup_url += credentials.split(':')[0]
            workgroup_url = "%s/%s" % (server, workgroup_url)
            info_str += " in Personal workspace (%s)" % workgroup_url
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
            raise CCTError("create module for %s request 1 failed: %s %s" %
                           (title, response1.status_code, response1.reason))
        cc_license = self.get_license(response1, logger)
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
            raise CCTError("create module for %s request 2 failed: %s %s" %
                           (title, response2.status_code, response2.reason))
        r2url = response2.url.encode('UTF-8')
        create_url = r2url[:regex.search('cc_license', r2url).start()]
        response3 = http.http_post_request("%scontent_title" % create_url, auth=auth, data=data3)
        if not http.verify(response3, logger):
            raise CCTError("create module for %s request 3 failed: %s %s" %
                           (title, response3.status_code, response3.reason))
        return create_url

    def publish_module(self, module_url, credentials, logger, new=True):
        """
        Publishes the module at [module_url] with [credentials] using HTTP requests.

        Returns the published module ID.
        Raises a CustomError on http request failure.
        """
        username, password = credentials.split(':')
        data1 = {"message": "created module", "form.button.publish": "Publish", "form.submitted": "1"}
        response1 = http.http_post_request("%smodule_publish_description" % module_url, auth=(username, password),
                                           data=data1)
        if not http.verify(response1, logger):

            raise CCTError("publish module for %s request 1 failed: %s %s" %
                           (module_url, response1.status_code, response1.reason))
        if new:
            data2 = {"message": "created module", "publish": "Yes, Publish"}
            response2 = http.http_post_request("%spublishContent" % module_url, auth=(username, password), data=data2)
            if not http.verify(response2, logger):
                raise CCTError("publish module for %s request 2 failed: %s %s" %
                               (module_url, response1.status_code, response1.reason))

            # extract module ID
            url = response2.url.encode('UTF-8')
            end_id = regex.search('/content_published', url).start()
            beg = url.rfind('/', 0, end_id) + 1
            return url[beg:end_id], url
        else:
            return module_url[module_url.rfind('/', 0, -1) + 1:-1], module_url

    def get_license(self, response, logger):
        try:
            html = response.text.encode('UTF-8', 'ignore')
            start = regex.search(r'<input\s*type="hidden"\s*name="license"\s*value="', html)
            return html[start.end():html.find('"', start.end())]
        except TerminateError:
            raise TerminateError("Terminate Signaled")
        except Exception as e:
            logger.debug("Failed to get license, defaulting to cc-by 4.0: %s" % e)
            logger.debug(traceback.format_exc())
            return "http://creativecommons.org/licenses/by/4.0/"

    def create_collection(self, credentials, title, server, logger):
        logger.info("Creating collection %s" % title)
        auth = tuple(credentials.split(':'))
        data0 = {"type_name": "Collection",
                 "workspace_factories:method": "Create New Item"}
        response0 = http.http_post_request("%s/Members/%s" % (server, auth[0]), auth=auth, data=data0)
        if not http.verify(response0, logger):
            raise CCTError("Creation of collection %s request 2 failed: %s %s" %
                           (title, response0.status_code, response0.reason))
        cc_license = self.get_license(response0, logger)
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
            raise CCTError("Creation of collection %s request 2 failed: %s %s" %
                           (title, response1.status_code, response1.reason))
        url = response1.url
        base = url[:url.rfind('/')+1]
        response2 = http.http_post_request("%s/content_title" % base, auth=auth, data=data2)
        if not http.verify(response2, None):
            raise CCTError("Creation of collection %s request 3 failed: %s %s" %
                           (title, response2.status_code, response2.reason))
        start = base[:-1].rfind('/')+1
        return Collection(title, str(base[start:-1]))

    def add_subcollections(self, titles, server, credentials, collection, logger):
        logger.info("Adding subcollections to collection %s: %s" % (collection.title, titles))
        auth = tuple(credentials.split(':'))
        base = "%s/Members/%s/%s/" % (server, auth[0], collection.get_parents_url())
        data4 = {"form.submitted": "1",
                 "titles": "\n".join(titles),
                 "submit": "Add new subcollections"}
        subcollection = '@@collection-composer-collection-subcollection'
        response = http.http_post_request(base + subcollection, auth=auth, data=data4)
        if not http.verify(response, logger):
            raise CCTError("Creation of subcollection(s) %s request failed: %s %s" %
                           (titles, response.status_code, response.reason))
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
            modules_str += "%s " % module.destination_id
        logger.info("Adding modules to collection %s: %s" % (collection.title, modules_str))
        auth = tuple(credentials.split(':'))
        data = {"form.submitted": "1",
                "form.action": "submit"}
        collection_url = collection.get_parents_url()
        for module in modules:
            if not module.valid:
                continue
            data["ids:list"] = module.destination_id
            response = http.http_post_request("%s/Members/%s/%s/@@collection-composer-collection-module" %
                                              (server, auth[0], collection_url), auth=auth, data=data)
            if not http.verify(response, logger):
                logger.error("Module %s failed to be added to collection %s" % (module.title, collection.title))
                module.valid = False
                failures.append((module.full_title(), " adding to collection"))
                continue

    def publish_collection(self, server, credentials, collection, logger):
        logger.info("Publishing collection %s" % collection.title)
        auth = tuple(credentials.split(':'))
        publish_message = "Initial publish"
        data1 = {"message": publish_message,
                 "form.button.publish": "Publish",
                 "form.submitted": "1"}
        response1 = http.http_post_request("%s/Members/%s/%s/collection_publish" % (server, auth[0], collection.id),
                                           auth=auth, data=data1)
        if not http.verify(response1, logger):
            raise CCTError("Publishing collection %s request 1 failed: %s %s" %
                           (collection.title, response1.status_code, response1.reason))
        data2 = {"message": publish_message,
                 "publish": "Yes, Publish"}
        response2 = http.http_post_request("%s/Members/%s/%s/publishContent" % (server, auth[0], collection.id),
                                           auth=auth, data=data2)
        if not http.verify(response2, logger):
            raise CCTError("Publishing collection %s request 2 failed: %s %s" %
                           (collection.title, response2.status_code, response2.reason))
