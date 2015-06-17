import csv
import re as regex
import datetime

class BookmapConfiguration:
    def __init__(self, chapter_number_column,
                       chapter_title_column,
                       module_title_column,
                       source_module_ID_column,
                       source_workgroup_column,
                       destination_module_ID_column,
                       destination_workgroup_column, strip_section_numbers):
        self.chapter_number_column = chapter_number_column
        self.chapter_title_column = chapter_title_column
        self.module_title_column = module_title_column
        self.source_module_ID_column = source_module_ID_column
        self.source_workgroup_column = source_workgroup_column
        self.destination_module_ID_column = destination_module_ID_column
        self.destination_workgroup_column = destination_workgroup_column
        self.strip_section_numbers = False
        if strip_section_numbers.lower() in ['yes', 'true']:
            self.strip_section_numbers = True

class Bookmap:
    def __init__(self, filename, bookmap_config, run_options):
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
        self.read_csv(filename)

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

    def convert(self, reader):
        bookmap = BookmapData()
        for row in reader:
            section_number, title = self.strip_section_numbers(row[self.config.module_title_column])
            module = CNXModule(title, section_number)
            # Read in available data from input file TODO make more extensible
            self.safe_process_column('module.source_id = row[self.config.source_module_ID_column]', row, module)
            self.safe_process_column('module.source_workspace_url = row[self.config.source_workgroup_column]', row, module)
            self.safe_process_column('module.destination_id = row[self.config.destination_module_ID_column]', row, module)
            self.safe_process_column('module.destination_workspace_url = row[self.config.destination_workgroup_column]', row, module)
            self.safe_process_column('module.chapter_number = row[self.config.chapter_number_column]', row, module)
            self.safe_process_column('module.chapter_title = row[self.config.chapter_title_column]', row, module)
            bookmap.add_module(module)
        if self.workgroups:
            for chapter in self.chapters:
                chapter_number_and_title = self.get_chapter_number_and_title(chapter)
                chapter_title = chapter_number_and_title.split(' ', 1)[1]
                wgtitle = self.booktitle+' - '+chapter_number_and_title+str(datetime.datetime.now())
                bookmap.add_workgroup(Workgroup(wgtitle, chapter_number=chapter, chapter_title=chapter_title))
        return bookmap

    def safe_process_column(self, expression, row, module):
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
        if regex.match('[0-9]', title):
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
        return ' '

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
        # chapter_number = module.get_chapter_number()
        out.append(module.chapter_number)
        out.append(module.chapter_title)  # self.get_chapter_title(chapter_number))  # chapter number and title for module
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


class Workspace:
    def __init__(self, url, modules=None):
        self.url = url
        if not modules:
            self.modules = []

    def add_module(self, module):
        self.modules.append(module)


class Workgroup(Workspace):
    def __init__(self, title, chapter_title='', id='', url='', modules=None, chapter_number='0'):
        self.title = title
        self.chapter_title = chapter_title
        self.id = id
        self.url = url
        if not modules:
            self.modules = []
        self.chapter_number = chapter_number

    def __str__(self):
        modules_str = ""
        for module in self.modules:
            modules_str += '\n\t'+str(module)
        return self.id+' '+self.title+' '+self.chapter_number+' '+self.chapter_title+' '+self.url+' '+modules_str


class CNXModule(object):
    def __init__(self, title,
                       section_number='',
                       source_workspace_url='',
                       source_id='',
                       destination_workspace_url='',
                       destination_id='',
                       chapter_title='',
                       chapter_number=''):
        self.title = title
        self.section_number = section_number
        self.source_workspace_url = source_workspace_url
        self.source_id = source_id
        self.destination_workspace_url = destination_workspace_url
        self.destination_id = destination_id
        self.chapter_title = chapter_title
        self.chapter_number = chapter_number

    def get_chapter_number(self):
        return self.section_number.split('.')[0]

    def __str__(self):
        return self.section_number+' '+self.title+' '+self.source_workspace_url+' '+self.source_id+' '+self.destination_workspace_url+' '+self.destination_id

