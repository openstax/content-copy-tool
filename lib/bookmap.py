import csv
import re as regex
import time

"""
This file contains the bookmap related objects.
"""


class BookmapConfiguration:
    """ Holds the settings of the bookmap """
    def __init__(self, chapter_number_column,
                       chapter_title_column,
                       module_title_column,
                       source_module_ID_column,
                       destination_module_ID_column,
                       destination_workgroup_column,
                       unit_number_column,
                       unit_title_column, strip_section_numbers):
        self.chapter_number_column = chapter_number_column
        self.chapter_title_column = chapter_title_column
        self.module_title_column = module_title_column
        self.source_module_ID_column = source_module_ID_column
        self.destination_module_ID_column = destination_module_ID_column
        self.destination_workgroup_column = destination_workgroup_column
        self.unit_number_column = unit_number_column
        self.unit_title_column = unit_title_column
        self.strip_section_numbers = False
        if strip_section_numbers.lower() in ['yes', 'true']:
            self.strip_section_numbers = True


class Bookmap:
    """ Represents the input data plus the input options """
    def __init__(self, filename, bookmap_config, run_options, logger):
        self.filename = filename
        self.config = bookmap_config
        self.booktitle = self.parse_book_title(filename)
        self.delimiter = ','
        if filename.endswith('.tsv'):
            self.delimiter = '\t'
        if not run_options.chapters:
            self.chapters = self.get_chapters()
        else:
            self.chapters = run_options.chapters
        if run_options.exclude:
            self.chapters = [chapter for chapter in self.chapters if chapter not in run_options.exclude]
        run_options.chapters = self.chapters
        self.workgroups = run_options.workgroups
        self.read_csv(filename, logger)

    def read_csv(self, filename, logger):
        """
        Reads in a csv file and returns a list of the entries, will also accept a
        tsv file.

        Each entry is a dictionary that maps the column title (first line in csv)
        to the row value (corresponding column in that row).

        Arguments:
            filename - the path to the input file.

        Returns:
            None
        """
        self.bookmap_raw = list(csv.DictReader(open(filename), delimiter=self.delimiter))
        self.bookmap = self.convert(logger, csv.DictReader(open(filename), delimiter=self.delimiter))

    def convert(self, logger, reader):
        """
        Reads the input raw data and converts it into the bookmap object.

        Arguments:
            reader - the reader that has opened the input file

        Returns:
            The internal BookmapData object with all of the parsed data from the input file.
        """
        bookmap = BookmapData()
        logger.debug("Columns from input file: %s" % reader.fieldnames)
        for row in reader:
            section_number, title = self.strip_section_numbers(row[self.config.module_title_column])
            module = CNXModule(title, section_number)
            # Read in available data from input file TODO make more extensible
            cmds = [('module.source_id', 'row[self.config.source_module_ID_column]', 'default'),
                    ('module.destination_id', 'row[self.config.destination_module_ID_column]', 'default'),
                    ('module.destination_id', 'row[self.config.destination_module_ID_column]', 'default'),
                    ('module.destination_workspace_url', 'row[self.config.destination_workgroup_column]', 'default'),
                    ('module.chapter_number', 'row[self.config.chapter_number_column]', 'default'),
                    ('module.chapter_title', 'row[self.config.chapter_title_column]', 'default'),
                    ('module.unit_number', 'row[self.config.unit_number_column]', 'default'),
                    ('module.unit_title', 'row[self.config.unit_title_column]', '""')
                    ]
            for cmd in cmds:
                self.safe_process_column(cmd[0], cmd[1], row, module, cmd[2])
            bookmap.add_module(module)
        for chapter in self.chapters:
            chapter_number_and_title = self.get_chapter_number_and_title(chapter)
            chapter_title = chapter_number_and_title.split(' ', 1)[1]
            wgtitle = "%s - %s" % (self.booktitle, chapter_number_and_title)
            new_workgroup = Workgroup(wgtitle, chapter_number=chapter, chapter_title=chapter_title)
            bookmap.add_workgroup(new_workgroup)
            for module in bookmap.modules:
                if module.chapter_number == chapter:
                    new_workgroup.add_module(module)
                    new_workgroup.url = module.destination_workspace_url
                    new_workgroup.unit_number = module.unit_number
                    new_workgroup.unit_title = module.unit_title
        return bookmap

    def safe_process_column(self, lhs, rhs, row, module, default=None):
        """ Catch the KeyError because not all columns are required. """
        try:
            exec "%s = %s" % (lhs, rhs)
        except KeyError:
            if default is None:
                return  # then we don't have that data, move on
            self.safe_process_column(lhs, default, row, module)

    def parse_book_title(self, filepath):
        """
        Parse the book title from the input file, assumes the input file is named:
        [Booktitle].csv or [Booktitle].tsv

        If the input file is a copy map (not a csv/tsv file), this will return the
        input filename, so for /path/to/file/myfile.out it will return myfile.out
        """
        if filepath.endswith('.csv'):
            return filepath[filepath.rfind('/') + 1:filepath.find('.csv')]
        if filepath.endswith('.tsv'):
            return filepath[filepath.rfind('/') + 1:filepath.find('.tsv')]
        else:
            return filepath[filepath.rfind('/') + 1:]

    def get_chapters(self):
        """ Returns a list of all the valid chapters in the bookmap """
        chapters = []
        for entry in csv.DictReader(open(self.filename), delimiter=self.delimiter):
            if not entry[self.config.chapter_number_column] in chapters:
                chapters.append(entry[self.config.chapter_number_column])
        return chapters

    def strip_section_numbers(self, title):
        """ Strips the section numbers from the module title """
        try:
            if regex.match('[0-9]', title):
                num = title[:str.index(title, ' '):]
                title = title[str.index(title, ' ') + 1:]
                return num, title
        except Exception, e:
            print "\033[91mError stripping section number from: [%s]. leaving title as is. \033[0m" % title
        return '', title

    def remove_invalid_modules(self):
        """ Removes invalid modules """
        self.bookmap[:] = [entry for entry in self.bookmap if self.is_valid(entry)]

    def is_valid(self, module):
        """ Determines if a module is valid or invalid """
        if module[self.config.module_title_column] == '' or module[self.config.module_title_column] == ' ':
            return False
        return True

    def get_chapter_number_and_title(self, chapter_num):
        """ Gets the title of the provided chapter number in the provide bookmap """
        for module in list(self.bookmap_raw):
            if module[self.config.chapter_number_column] == str(chapter_num):
                return "%s %s" % (module[self.config.chapter_number_column], module[self.config.chapter_title_column])
        return " "

    def save(self, units, error=False):
        """ Saves the bookmap object to a file with same format as the input file. """

        parts = self.filename.split('.')
        save_file = "%s_output_%s.%s" % (parts[0], time.strftime("%Y%m%d-%H%M%S"), parts[1])
        if error:
            save_file = "%s_error_%s.%s" % (parts[0], time.strftime("%Y%m%d-%H%M%S"), parts[1])
        columns = [self.config.chapter_number_column,
                   self.config.chapter_title_column,
                   self.config.module_title_column,
                   self.config.source_module_ID_column,
                   self.config.destination_module_ID_column,
                   self.config.destination_workgroup_column]
        if units:
            columns.insert(0, self.config.unit_title_column)
            columns.insert(0, self.config.unit_number_column)

        with open(save_file, 'w') as csvoutput:
            writer = csv.writer(csvoutput, lineterminator='\n', delimiter=self.delimiter)
            all = []
            all.append(columns)
            for module in self.bookmap.modules:
                all.append(self.bookmap.output(module, units))
            writer.writerows(all)
        return save_file


class BookmapData:
    """ The data structure that holds the bookmap input data. """
    def __init__(self):
        self.modules = []
        self.workgroups = []

    def add_module(self, module):
        self.modules.append(module)

    def add_workgroup(self, workgroup):
        self.workgroups.append(workgroup)

    def output(self, module, units):
        """
        Compiles the output data for the given module.

        Returns:
            A list of the data that goes in the output file for this module.
        """
        out = []
        if units:
            out.append(module.unit_number)
            out.append(module.unit_title)
        out.append(module.chapter_number)
        out.append(module.chapter_title)
        module_title_entry = module.title
        if module.section_number:
            module_title_entry = "%s %s" % (module.section_number, module_title_entry)
        out.append(module_title_entry)
        out.append(module.source_id)
        out.append(module.destination_id)
        out.append(module.destination_workspace_url)
        return out

    def get_chapter_title(self, chap_number):
        titles = [workgroup.chapter_title for workgroup in self.workgroups if workgroup.chapter_number == chap_number]
        if titles:
            return titles[0]
        return ""

    def __str__(self):
        thestr = ""
        for workgroup in self.workgroups:
            thestr += str(workgroup)
        thestr += '\n'
        for module in self.modules:
            thestr += "%s\n" % module
        return thestr


class Collection:
    def __init__(self, title, collection_id='', parent=None):
        self.title = title
        self.id = collection_id
        self.parent = parent
        self.members = []

    def add_member(self, member):
        self.members.append(member)

    def get_parents(self):
        parents = []
        next_parent = self.parent
        while next_parent is not None:
            parents.append(next_parent)
            next_parent = next_parent.parent
        return parents

    def get_parents_url(self):
        parents = self.get_parents()
        url = self.id
        if parents is None:
            return url
        for parent in parents:
            url = "%s/%s" % (parent.id, url)
        return url

    def __str__(self):
        members_string = ""
        for member in self.members:
            members_string += "%s, " % member
        return "%s %s %s" % (self.title, self.id, members_string)


class Workspace:
    def __init__(self, url, modules=None):
        self.url = url
        if not modules:
            self.modules = []

    def add_module(self, module):
        self.modules.append(module)


class Workgroup(Workspace):
    def __init__(self, title, chapter_title='', id='', url='', modules=None, chapter_number='0', unit_number=''):
        self.title = title
        self.chapter_title = chapter_title
        self.id = id
        self.url = url
        if not modules:
            self.modules = []
        self.chapter_number = chapter_number
        self.unit_number = unit_number

    def __str__(self):
        modules_str = ""
        for module in self.modules:
            modules_str += '\n\t' + str(module)
        return "%s %s: [%s] %s \"%s\": %s" % \
               (self.id, self.title, self.chapter_number, self.chapter_title, self.url, modules_str)


class CNXModule(object):
    def __init__(self, title,
                       section_number='',
                       source_id='',
                       destination_workspace_url='',
                       destination_id='',
                       chapter_title='',
                       chapter_number='',
                       unit_number='',
                       unit_title=''):
        self.title = title
        self.section_number = section_number
        self.source_id = source_id
        self.destination_workspace_url = destination_workspace_url
        self.destination_id = destination_id
        self.chapter_title = chapter_title
        self.chapter_number = chapter_number
        self.unit_number = unit_number
        self.unit_title = unit_title
        self.valid = True

    def get_chapter_number(self):
        return self.section_number.split('.')[0]

    def full_title(self):
        if self.section_number != '' and self.section_number != ' ' or self.section_number is not None:
            return "%s %s" % (self.section_number, self.title)
        else:
            return self.title

    def __str__(self):
        return "%s %s %s %s %s" % \
               (self.section_number, self.title, self.source_id, self.destination_workspace_url, self.destination_id)
