import csv
from tempfile import mkstemp
from shutil import move
from os import remove, close
import re
"""
This file contains utility functions relative to input to the content-copy-tool
"""

def read_csv(filename):
    """
    Reads in a csv file and returns a list of the entries, will also accept a
    tsv file.

    Each entry is a dictionary that maps the column title (first line in csv)
    to the row value (corresponding column in that row).

    Alternatively, if the file is a .out, it will return a read version of that.
    """
    if filename.endswith('.out'):
        return read_copy_map(filename), False
    delimiter = ','
    if filename.endswith('.tsv'):
        delimiter = '\t'
    bookmap = csv.DictReader(open(filename), delimiter=delimiter)
    return list(bookmap), True

def read_copy_map(filename):
    """ The copy map is a text file with lines of space separated values """
    file = open(filename)
    map = []
    for line in file:
        map.append(line.split(' '))
    return map

def is_valid(module, module_title_column):
    """ Determines if a module is valid or invalid """
    if module[module_title_column] is '' or module[module_title_column] is ' ':
        return False
    return True

def remove_invalid_modules(bookmap, module_title_column):
    """ Removes invalid modules """
    bookmap[:] = [entry for entry in bookmap if is_valid(entry, module_title_column)]

def strip_section_numbers(bookmap, module_title_column):
    """ Strips the section numbers from the module title """
    for module in bookmap:
        if re.match('[0-9]', module[module_title_column]):
            with_num = module[module_title_column]
            without_num = with_num[str.index(with_num, ' ')+1:]
            module[module_title_column] = without_num

def get_chapter_number_and_title(bookmap, chapter_num, chapter_number_column, chapter_title_column):
    """ Gets the title of the provided chapter number in the provide bookmap """
    for module in bookmap:
        if module[chapter_number_column] is str(chapter_num):
            return module[chapter_number_column]+' '+module[chapter_title_column]
    return ''

def parse_book_title(filepath):
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

def get_chapters(bookmap, chapter_number_column):
    """ Returns a list of all the valid chapters in the bookmap """
    chapters = []
    for entry in bookmap:
        if not entry[chapter_number_column] in chapters:
            chapters.append(entry[chapter_number_column])
    return chapters

def prepare_role_updates(metadatafile, config):
    """
    Updates the roles on a module. This reads in from the settings file for
    creator, maintainer, and rightsholder configuration.
    """
    creators = list(config['creators'])
    rightsholders = list(config['rightsholders'])
    maintainers = list(config['maintainers'])

    if len(creators) == 1:
        creator_string = '<dcterms:creator oerdc:id="'+creators[0]+'"'
    else:
        creator_string = '<dcterms:creator oerdc:id="'
        for creator in creators[:-1]:
            creator_string += creator+'" oerdc:email="useremail2@localhost.net" oerdc:pending="False">firstname2 lastname2</dcterms:creator>\n<dcterms:creator oerdc:id="'
        creator_string += creators[-1]+'"'
    creator_tuple = ('<dcterms:creator oerdc:id=".*"', creator_string)

    if len(maintainers) == 1:
        maintainer_string = '<oerdc:maintainer oerdc:id="'+maintainers[0]+'"'
    else:
        maintainer_string = '<oerdc:maintainer oerdc:id="'
        for maintainer in maintainers[:-1]:
            maintainer_string += maintainer+'" oerdc:email="useremail2@localhost.net" oerdc:pending="False">firstname2 lastname2</oerdc:maintainer>\n<oerdc:maintainer oerdc:id="'
        maintainer_string += maintainers[-1]+'"'
    maintainer_tuple = ('<oerdc:maintainer oerdc:id=".*"', maintainer_string)

    if len(rightsholders) == 1:
        rightholder_string = '<dcterms:rightsHolder oerdc:id="'+rightsholders[0]+'"'
    else:
        rightsholder_string = '<dcterms:rightsHolder oerdc:id="'
        for rightsholder in rightsholders[:-1]:
            rightsholder_string += rightsholder+'" oerdc:email="useremail2@localhost.net" oerdc:pending="False">firstname2 lastname2</dcterms:rightsHolder>\n<dcterms:rightsHolder oerdc:id="'
        rightsholder_string += rightsholders[-1]+'"'
    rightsholder_tuple = ('<dcterms:rightsHolder oerdc:id=".*"', rightsholder_string)

    replace_map = [creator_tuple, maintainer_tuple, rightsholder_tuple]
    return replace_map

def update_roles(file_path, replace_map):
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
    # Remove original file
    remove(file_path)
    # Move new file
    move(abs_path, file_path)
