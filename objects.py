import csv
from tempfile import mkstemp
from shutil import move, rmtree
from os import close, remove, path, walk
import re
import zipfile
import http_util as http
import requests
from configuration_objects import *
import datetime

# Operation Objects
class RoleUpdater:
    def run_update_roles(self, xmlfile, role_configuration):
        self.update_roles(xmlfile, self.prepare_role_updates(xmlfile, role_configuration))

    def update_roles(self, file_path, replace_map):
        """
        Reads through the input file and replaces content according to the replace map

        The replace_map is a list of tuples: (pattern, substitute text)
        """
        fh, abs_path = mkstemp()
        with open(abs_path,'w') as new_file:
            with open(file_path) as old_file:
                for line in old_file:
                    for pattern, subst in replace_map:
                        line = re.sub(pattern, subst, line)
                    new_file.write(line)
        close(fh)
        remove(file_path)  # Remove original file
        move(abs_path, file_path)  # Move new file

    def prepare_role_updates(self, config):
        """
        Updates the roles on a module. This reads in from the settings file for
        creator, maintainer, and rightsholder configuration.
        """

        if len(config.creators) == 1:
            creator_string = '<dcterms:creator oerdc:id="'+config.creators[0]+'"'
        else:
            creator_string = '<dcterms:creator oerdc:id="'
            for creator in config.creators[:-1]:
                creator_string += creator+'" oerdc:email="useremail2@localhost.net" oerdc:pending="False">firstname2 lastname2</dcterms:creator>\n<dcterms:creator oerdc:id="'
            creator_string += config.creators[-1]+'"'
        creator_tuple = ('<dcterms:creator oerdc:id=".*"', creator_string)

        if len(config.maintainers) == 1:
            maintainer_string = '<oerdc:maintainer oerdc:id="'+config.maintainers[0]+'"'
        else:
            maintainer_string = '<oerdc:maintainer oerdc:id="'
            for maintainer in config.maintainers[:-1]:
                maintainer_string += maintainer+'" oerdc:email="useremail2@localhost.net" oerdc:pending="False">firstname2 lastname2</oerdc:maintainer>\n<oerdc:maintainer oerdc:id="'
            maintainer_string += config.maintainers[-1]+'"'
        maintainer_tuple = ('<oerdc:maintainer oerdc:id=".*"', maintainer_string)

        if len(config.rightholders) == 1:
            rightholder_string = '<dcterms:rightsHolder oerdc:id="'+config.rightholders[0]+'"'
        else:
            rightholder_string = '<dcterms:rightsHolder oerdc:id="'
            for rightholder in config.rightholders[:-1]:
                rightholder_string += rightholder+'" oerdc:email="useremail2@localhost.net" oerdc:pending="False">firstname2 lastname2</dcterms:rightsHolder>\n<dcterms:rightsHolder oerdc:id="'
            rightholder_string += config.rightholders[-1]+'"'
        rightholder_tuple = ('<dcterms:rightsHolder oerdc:id=".*"', rightholder_string)

        replace_map = [creator_tuple, maintainer_tuple, rightholder_tuple]
        return replace_map

    def get_pending_roles_request_ids(self, copy_config, credentials):
        ids = []
        auth = tuple(credentials.split(':'))
        response1 = http.http_get_request(copy_config.destination_server+'/collaborations', auth=auth)
        if not http.verify(response1):
            print "FAILURE", response1.status_code, response1.reason
        else:
            html = response1.text
            pattern = re.compile('name="ids:list" value=".*"')
            matching_items = re.finditer(pattern, html)
            for match in matching_items:
                string = match.group(0)
                print string
                ids.append(string[string.find('value="')+7:-1])
        return ids

    def get_users_of_roles(self):
        # TODO get all the users in the new roles (the ones with pending role requests)
        return ['user1:user1', 'user3:user3']

    def accept_roles(self, copy_config):
        users = self.get_users_of_roles()
        for user in users:
            parameters = "?"
            for id in self.get_pending_roles_request_ids(copy_config, user):
                parameters += "ids%3Alist="+id+"&"
            parameters += 'agree=&accept=+Accept+'  # rest of form
            auth = tuple(user.split(':'))
            response = http.http_get_request(copy_config.destination_server+'/updateCollaborations'+parameters, auth=auth) # yes, it is a GET request
            if not http.verify(response):
                print "ERROR accepting pending requests for "+auth[0]+str(response.status_code)+' '+response.reason


class Bookmap:
    def __init__(self, filename, bookmap_config, chapters, workgroups):
        self.filename = filename
        self.config = bookmap_config
        self.booktitle = self.parse_book_title(filename)
        self.delimiter = ','
        if filename.endswith('.tsv'):
            self.delimiter = '\t'
        if not chapters:
            self.chapters = self.get_chapters()
        else:
            self.chapters = chapters
        self.workgroups = workgroups
        self.placeholders = self.read_csv(filename)

    def read_csv(self, filename):
        """
        Reads in a csv file and returns a list of the entries, will also accept a
        tsv file.

        Each entry is a dictionary that maps the column title (first line in csv)
        to the row value (corresponding column in that row).

        TODO update docstring
        Alternatively, if the file is a .out, it will return a read version of that.
        """
        self.bookmap_raw = list(csv.DictReader(open(filename), delimiter=self.delimiter))
        self.bookmap = self.convert(csv.DictReader(open(filename), delimiter=self.delimiter))
        if filename.endswith('.out') or filename.startswith("OUT-"):
            return False
        return True

    def convert(self, reader):
        bookmap = BookmapData()
        for row in reader:
            section_number, title = self.strip_section_numbers(row[self.config.module_title_column])
            module = CNXModule(title, section_number)
            # Read in available data from input file TODO make more extensible
            self.safe_process_column('module.source_id = row[self.config.source_module_ID_column]')
            self.safe_process_column('module.source_workspace_url = row[self.config.source_workgroup_column]')
            self.safe_process_column('module.destination_id = row[self.config.destination_module_ID_column]')
            self.safe_process_column('module.destination_workspace_url = row[self.config.destination_workgroup_column]')
            bookmap.add_module(module)
        if self.workgroups:
            for chapter in self.chapters:
                chapter_number_and_title = self.get_chapter_number_and_title(chapter)
                chapter_title = chapter_number_and_title.split(' ', 1)[1]
                wgtitle = self.booktitle+' - '+chapter_number_and_title+str(datetime.datetime.now())
                bookmap.add_workgroup(Workgroup(wgtitle, chapter_number=chapter, chapter_title=chapter_title))
        return bookmap

    def safe_process_column(self, expression):
        try:
            exec expression
        except KeyError:
            pass  # then we don't have that data, move on

    def parse_book_title(self, filepath):
        """
        Parse the book title from the input file, assumes the input file is named:
        [Booktitle].csv or [Booktitle].tsv

        If the input file is a copy map (not a csv/tsv file), this will return the
        input filename, so for /path/to/file/myfile.out it will return myfile.out
        """
        if filepath.endswith('.csv'):
            return filepath[filepath.rfind('/')+1:filepath.find('.csv')]
        if filepath.endswith('.tsv'):
            return filepath[filepath.rfind('/')+1:filepath.find('.tsv')]
        else:
            return filepath[filepath.rfind('/')+1:]

    def get_chapters(self):
        """ Returns a list of all the valid chapters in the bookmap """
        chapters = []
        for entry in csv.DictReader(open(self.filename), delimiter=self.delimiter):
            if not entry[self.config.chapter_number_column] in chapters:
                chapters.append(entry[self.config.chapter_number_column])
        return chapters

    def strip_section_numbers(self, title):
        """ Strips the section numbers from the module title """
        if re.match('[0-9]', title):
            num = title[:str.index(title, ' '):]
            title = title[str.index(title, ' ')+1:]
            return num, title
        return '', title

    def remove_invalid_modules(self):
        """ Removes invalid modules """
        self.bookmap[:] = [entry for entry in self.bookmap if self.is_valid(entry)]

    def is_valid(self, module):
        """ Determines if a module is valid or invalid """
        if module[self.config.module_title_column] is '' or module[self.config.module_title_column] is ' ':
            return False
        return True

    def get_chapter_number_and_title(self, chapter_num):
        """ Gets the title of the provided chapter number in the provide bookmap """
        for module in list(self.bookmap_raw):
            if module[self.config.chapter_number_column] is str(chapter_num):
                return module[self.config.chapter_number_column]+' '+module[self.config.chapter_title_column]
        return ''

    def save(self):
        save_file = 'OUT-'+self.filename
        columns = [self.config.chapter_number_column,
                   self.config.chapter_title_column,
                   self.config.module_title_column,
                   self.config.source_module_ID_column,
                   self.config.source_workgroup_column,
                   self.config.destination_module_ID_column,
                   self.config.destination_workgroup_column]

        with open(save_file, 'w') as csvoutput:
            writer = csv.writer(csvoutput, lineterminator='\n', delimiter=self.delimiter)
            all = []
            all.append(columns)
            for module in self.bookmap.modules:
                all.append(self.bookmap.output(module))
            writer.writerows(all)
        return save_file


class BookmapData:
    def __init__(self):
        self.modules = []
        self.workgroups = []

    def add_module(self, module):
        self.modules.append(module)

    def add_workgroup(self, workgroup):
        self.workgroups.append(workgroup)

    def output(self, module):
        out = []
        chapter_number = module.get_chapter_number()
        out.append(chapter_number)
        out.append(self.get_chapter_title(chapter_number)) # chapter number and title for module
        module_title_entry = module.title
        if module.section_number:
            module_title_entry = module.section_number+' '+module_title_entry
        out.append(module_title_entry)
        out.append(module.source_id)
        out.append(module.source_workspace_url)
        out.append(module.destination_id)
        out.append(module.destination_workspace_url)
        return out

    def get_chapter_title(self, chapter_number):
        titles = [workgroup.chapter_title for workgroup in self.workgroups if workgroup.chapter_number is chapter_number]
        if titles:
            return titles[0]
        return ""

    def __str__(self):
        thestr = ""
        for workgroup in self.workgroups:
            thestr += str(workgroup)
        thestr += '\n'
        for module in self.modules:
            thestr += str(module)+'\n'
        return thestr


class Copier:
    def __init__(self, config, copy_map):
        self.config = config
        self.copy_map = copy_map

    def extract_zip(self, zipfilepath):
        with zipfile.ZipFile(zipfilepath, "r") as zip:
            temp_item = zip.namelist()[0]
            dir = temp_item[:temp_item.find('/')]
            zip.extractall()
        return dir

    def remove_file_from_dir(self, directory, file):
        os.remove(directory+'/'+file)

    def zipdir(self, file_path, zipfilename):
        zipf = zipfile.ZipFile(zipfilename, 'w')
        for root, dirs, files in walk(file_path):
            for file in files:
                zipf.write(path.join(root, file))
        zipf.close()
        rmtree(path)

    def clean_zip(self, zipfile):
        dir = self.extract_zip(zipfile)
        remove(zipfile)
        zipdir = path.dirname(path.realpath(__file__))+'/'+dir
        self.remove_file_from_dir(zipdir, 'index.cnxml.html')
        self.zipdir(zipdir, zipfile)

    def copy_content(self, role_config, run_options, logger):
        """
        Copies content from source server to server specified by each entry in the
        content copy map.

        Arguments:
        TODO update docstring
          config           - the configuration from the settings file
          content_copy_map - a list of triples containing an entry for each module
                             to copy, format is:
            '[destination workgroup url] [destination module ID] [source module ID]'
          logger           - a reference to the tool's logger

        Returns:
          Nothing. It will, however, leave temporary & downloaded files for content
          that did not succeed in transfer.
        """
        for module in self.copy_map.modules:
            files = []
            logger.info("Copying content for module: "+module.source_id)
            if not run_options.dryrun:
                files.append(http.http_download_file(self.config.source_server+'/content/'+module.source_id+'/latest/module_export?format=zip', module.source_id, '.zip'))
                files.append(http.http_download_file(self.config.source_server+'/content/'+module.source_id+'/latest/rhaptos-deposit-receipt', module.source_id, '.xml'))
                if run_options.roles:
                    RoleUpdater().run_update_roles(module.source_id+'.xml', role_config)

                self.clean_zip(module.source_id+'.zip')  # remove index.cnxml.html from zipfile

                res, mpart = http.http_upload_file(module.source_id+'.xml', module.source_id+'.zip', module.destination_workspace_url+"/"+module.destination_id+'/sword', self.config.credentials)
                files.append(mpart)
                # clean up temp files
                if res.status < 400:
                    for temp_file in files:
                        remove(temp_file)
                else:
                    print res.status, res.reason  # TODO better handle for production


class CustomError(Exception):
    def __init__(self, arg):
        self.msg = arg


class Workspace:
    def __init__(self, url, modules=None):
        self.url = url
        if not modules:
            self.modules = []

    def add_module(self, module):
        self.modules.append(module)


class Workgroup(Workspace):
    def __init__(self, title, chapter_title='', id='', url='', modules=None, chapter_number='0'):
        super(url, modules)
        self.title = title
        self.chapter_title = chapter_title
        self.id = id
        self.chapter_number = chapter_number

    def __str__(self):
        modules_str = ""
        for module in self.modules:
            modules_str += '\n\t'+str(module)
        return self.id+' '+self.title+' '+self.chapter_number+' '+self.chapter_title+' '+self.url+' '+modules_str


class CNXModule(object):
    def __init__(self, title, section_number='', source_workspace_url='', source_id='', destination_workspace_url='', destination_id=''):
        self.title = title
        self.section_number = section_number
        self.source_workspace_url = source_workspace_url
        self.source_id = source_id
        self.destination_workspace_url = destination_workspace_url
        self.destination_id = destination_id

    def get_chapter_number(self):
        return self.section_number.split('.')[0]

    def __str__(self):
        return self.section_number+' '+self.title+' '+self.source_workspace_url+' '+self.source_id+' '+self.destination_workspace_url+' '+self.destination_id


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
            except CustomError, error:
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
        response = http.http_post_request(server+'/create_workgroup', auth=(username, password), data=data)
        if not http.verify(response):
            raise CustomError(str(response.status_code)+' '+response.reason)

        # extract workgroup ID
        url = response.url.encode('UTF-8')
        id_start = re.search('GroupWorkspaces/', url).end()
        id_end = url.find('/', id_start)
        workgroup.id = url[id_start:id_end]
        workgroup.url = url[:id_end]

    def run_create_and_publish_module(self, module, server, credentials, logger, workgroup_url='Members/', dryrun=False):
        """
        Uses HTTP requests to create and publish a module with the given information
        TODO update docstring
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
        info_str = "Creating module: "+module.title+" on "+server
        if workgroup_url is not 'Members/':
            info_str += " in workgroup: "+ workgroup_url
        else:
            workgroup_url += credentials.split(':')[0]
            workgroup_url = server+'/'+workgroup_url
            info_str += " in Personal workspace ("+workgroup_url+")"
        logger.info(info_str)
        if not dryrun:
            temp_url = self.create_module(module.title, credentials, workgroup_url)
            res, url = self.publish_module(temp_url, credentials)
            module.destination_workspace_url = workgroup_url
            module.destination_id = res

    def create_module(self, title, credentials, workspace_url):
        """
        Creates a module with [title] in [workspace_url] with [credentials].

        Returns the url of the created module, Fail on failure.
        """
        username, password = credentials.split(':')
        auth = username, password

        data1 = {"type_name": "Module", "workspace_factories:method": "Create New Item"}
        data2 = {"agree": "on", "form.button.next": "Next >>", "license": "http://creativecommons.org/licenses/by/4.0/", "form.submitted": "1"}
        data3 = {"title": title, "master_language": "en", "language": "en", "license": "http://creativecommons.org/licenses/by/4.0/", "form.button.next": "Next >>", "form.submitted": "1"}

        response1 = http.http_post_request(workspace_url, auth=auth, data=data1)
        if not http.verify(response1):
            raise CustomError('create_module request 1: '+response1.status_code+' '+response1.reason)
        response2 = http.http_post_request(response1.url.encode('UTF-8'), auth=auth, data=data2)
        if not http.verify(response2):
            raise CustomError('create_module request 2: '+response2.status_code+' '+response2.reason)
        r2url = response2.url.encode('UTF-8')
        create_url = r2url[:re.search('cc_license', r2url).start()]
        response3 = http.http_post_request(create_url + 'content_title', auth=auth, data=data3)
        if not http.verify(response3):
            raise CustomError('create_module request 3: '+response3.status_code+' '+response3.reason)
        return create_url

    def publish_module(self, module_url, credentials, new=True):
        """
        Publishes the module at [module_url] with [credentials] using HTTP requests.

        Returns:
          The published module ID, FAIL on failure.
        """
        username, password = credentials.split(':')
        data1 = {"message": "created module", "form.button.publish": "Publish", "form.submitted": "1"}
        response1 = http.http_post_request(module_url+'module_publish_description', auth=(username, password), data=data1)
        if not http.verify(response1):
            raise CustomError('publish module request 1: '+response1.status_code+' '+response1.reason)
        if new:
            data2 = {"message": "created module", "publish": "Yes, Publish"}
            response2 = http.http_post_request(module_url+'publishContent', auth=(username, password), data=data2)
            if not http.verify(response2):
                raise CustomError('publish module request 1: '+response1.status_code+' '+response1.reason)

            # extract module ID
            url = response2.url.encode('UTF-8')
            end_id = re.search('/content_published',url).start()
            beg = url.rfind('/', 0, end_id)+1
            return url[beg:end_id], url
        else:
            return module_url[module_url.rfind('/', 0, -1)+1:-1], module_url
