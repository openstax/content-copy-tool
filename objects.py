import csv
from tempfile import mkstemp
import shutil
import os
import re
import zipfile
import http_util as http
import cnx_util as cnx

# Configuration Objects
class CopyConfiguration:
    def __init__(self, source_server, destination_server, credentials):
        self.source_server = source_server
        self.destination_server = destination_server
        self.credentials = credentials


class BookmapConfiguration:
    """ Object that holds the bookmap configuration: the column names """
    def __init__(self, chapter_number_column, chapter_title_column, module_title_column, module_ID_column):
        self.chapter_number_column = chapter_number_column
        self.chapter_title_column = chapter_title_column
        self.module_title_column = module_title_column
        self.module_ID_column = module_ID_column


class RunOptions:
    def __init__(self, workgroups, copy, roles, accept_roles, publish, chapters, dryrun, selenium=False):
        self.workgroups = workgroups
        self.copy = copy
        self.roles = roles
        self.accept_roles = accept_roles
        self.publish = publish
        self.chapters = chapters
        self.dryrun = dryrun
        self.selenium = selenium

class RoleConfiguration:
    def __init__(self, creators, maintainers, rightholders):
        self.creators = creators
        self.maintainers = maintainers
        self.rightholders = rightholders


class RunConfiguration:
    def __init__(self, settings, input, logger, run_options, copy_config, bookmap_config):
        self.settings = settings
        self.input_file = input
        self.logger = logger
        self.run_options = run_options
        self.copy_config = copy_config
        self.bookmap_config = bookmap_config


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
        os.close(fh)
        # Remove original file
        os.remove(file_path)
        # Move new file
        shutil.move(abs_path, file_path)

    def prepare_role_updates(self, metadatafile, config):
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

    def get_pending_roles_request_ids(copy_config, credentials):
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
            for id in cnx.get_pending_roles_request_ids(copy_config, user):
                parameters += "ids%3Alist="+id+"&"
            parameters += 'agree=&accept=+Accept+' # rest of form.
            auth = tuple(user.split(':'))
            response = http.http_get_request(copy_config.destination_server+'/updateCollaborations'+parameters, auth=auth) # yes, it is a GET request
            if not http.verify(response):
                print "ERROR accepting pending requests for "+auth[0]+str(response.status_code)+' '+response.reason


class Bookmap:
    def __init__(self, filename, bookmap_config):
        self.filename = filename
        self.config = bookmap_config
        self.placeholders = self.read_csv(filename)
        self.booktitle = self.parse_book_title(filename)
        if self.placeholders:
            self.remove_invalid_modules()
            self.strip_section_numbers()

    def read_csv(self, filename):
        """
        Reads in a csv file and returns a list of the entries, will also accept a
        tsv file.

        Each entry is a dictionary that maps the column title (first line in csv)
        to the row value (corresponding column in that row).

        TODO update docstring Alternatively, if the file is a .out, it will return a read version of that.
        """
        if filename.endswith('.out'):
            return False
        delimiter = ','
        if filename.endswith('.tsv'):
            delimiter = '\t'
        self.bookmap = list(csv.DictReader(open(filename), delimiter=delimiter))
        return True

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
        for entry in self.bookmap:
            if not entry[self.config.chapter_number_column] in chapters:
                chapters.append(entry[self.config.chapter_number_column])
        return chapters

    def strip_section_numbers(self):
        """ Strips the section numbers from the module title """
        for module in self.bookmap:
            if re.match('[0-9]', module[self.config.module_title_column]):
                with_num = module[self.config.module_title_column]
                without_num = with_num[str.index(with_num, ' ')+1:]
                module[self.config.module_title_column] = without_num

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
        for module in self.bookmap:
            if module[self.config.chapter_number_column] is str(chapter_num):
                return module[self.config.chapter_number_column]+' '+module[self.config.chapter_title_column]
        return ''


class Copier:
    def __init__(self, config, file=None, object=None):
        self.config = config
        if file:
            self.copy_map = self.read_copy_map(file)
        elif object:
            self.copy_map = object
        else:
            raise ValueError('Either file or object must be set.')

    def read_copy_map(self, filename):
        """ The copy map is a text file with lines of space separated values """
        file = open(filename)
        map = []
        for line in file:
            map.append(line.split(' '))
        return map

    @staticmethod
    def record_creation(datalist, args):
        """ Appends a tuple of the args to the datalist """
        datalist.append(tuple(element for element in args))

    @staticmethod
    def write_list_to_file(datalist, booktitle):
        """
        Writes the data list to an output file.

        The output file is named: [booktitle].out and the data list may be of
        varying format. Each entry in the list will be written out to the file
        where each element in each entry will be separated by a space character.

        For example:
        [['a', 'b', 'c'], ['d','e'], ['f']]

        will look like:

        a b c
        d e
        f

        """
        filename = booktitle+'.out'#str(datetime.datetime.now())+'.out'
        file = open(filename, 'w')
        for entry in datalist:
            outstr = str(entry[0])
            for item in entry[1:]:
                outstr += ' '+str(item)
            outstr += '\n'
            file.write(outstr)
        file.close()
        return filename

    def extract_zip(self, zipfilepath):
        with zipfile.ZipFile(zipfilepath, "r") as zip:
            temp_item = zip.namelist()[0]
            dir = temp_item[:temp_item.find('/')]
            zip.extractall()
        return dir

    def remove_file_from_dir(self, directory, file):
        os.remove(directory+'/'+file)

    def zipdir(self, path, zipfilename):
        zipf = zipfile.ZipFile(zipfilename, 'w')
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for file in files:
                zipf.write(os.path.join(root, file))
        zipf.close()
        # print 'removing ', path
        shutil.rmtree(path)

    def clean_zip(self, zipfile):
        dir = self.extract_zip(zipfile)
        os.remove(zipfile)
        zipdir = os.path.dirname(os.path.realpath(__file__))+'/'+dir
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
        for entry in self.copy_map:
            try:
                source_moduleID = entry[2].strip('\n')
                destination_moduleID = entry[1]
                destination_workgroup = entry[0]
            except IndexError:
                logger.error("\033[91mFailure reading content for module, skipping.\033[0m")
                continue
            files = []
            logger.info("Copying content for module: "+source_moduleID)
            if not run_options.dryrun:
                files.append(http.http_download_file(self.config.source_server+'/content/'+source_moduleID+'/latest/module_export?format=zip', source_moduleID, '.zip'))
                files.append(http.http_download_file(self.config.source_server+'/content/'+source_moduleID+'/latest/rhaptos-deposit-receipt', source_moduleID, '.xml'))
                if run_options.roles:
                    RoleUpdater().run_update_roles(source_moduleID+'.xml', role_config)

                # remove index.cnxml.html from zipfile
                self.clean_zip(source_moduleID+'.zip')

                res, mpart = http.http_upload_file(source_moduleID+'.xml',source_moduleID+'.zip', destination_workgroup+"/"+destination_moduleID+'/sword', self.config.credentials)
                files.append(mpart)
                # clean up temp files
                if res.status < 400:
                    for file in files:
                        os.remove(file)
                else:
                    print res.status, res.reason # TODO better handle for production
