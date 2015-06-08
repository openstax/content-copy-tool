import csv
from tempfile import mkstemp
from shutil import move
from os import remove, close
import re

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
    if filepath.endswith('.csv'):
        return filepath[filepath.rfind('/')+1:filepath.find('.csv')]
    if filepath.endswith('.tsv'):
        return filepath[filepath.rfind('/')+1:filepath.find('.tsv')]
    else:
        return filepath[filepath.rfind('/')+1:]

def get_chapters(bookmap, chapter_number_column):
    chapters = []
    for entry in bookmap:
        if not entry[chapter_number_column] in chapters:
            chapters.append(entry[chapter_number_column])
    return chapters

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
