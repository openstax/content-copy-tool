import csv
import re

def read_csv(filename):
    """
    Reads in a csv file and returns a list of the entries

    Each entry is a dictionary that maps the column title (first line in csv)
    to the row value (corresponding column in that row).

    """
    bookmap = csv.DictReader(open(filename))
    return list(bookmap)

def is_valid(module):
    """ Determines if a module is valid or invalid """
    if module['Module Title'] is '' or module['Module Title'] is ' ':
        return False
    return True

def remove_invalid_modules(bookmap):
    """ Removes invalid modules """
    bookmap[:] = [entry for entry in bookmap if is_valid(entry)]

def strip_section_numbers(bookmap):
    """ Strips the section numbers from the module title """
    for module in bookmap:
        if re.match('[0-9]', module['Module Title']):
            with_num = module['Module Title']
            without_num = with_num[str.index(with_num, ' ')+1:]
            module['Module Title'] = without_num

def get_chapter_number_and_title(bookmap, chapter_num):
    """ Gets the title of the provided chapter number in the provide bookmap """
    for module in bookmap:
        if module['Chapter Number'] is str(chapter_num):
            return module['Chapter Number']+' '+module['Chapter Title']
    return ''

def parse_book_title(filepath):
    return filepath[filepath.rfind('/')+1:filepath.find('.csv')]

def get_chapters(bookmap):
    chapters = []
    for entry in bookmap:
        if not entry['Chapter Number'] in chapters:
            chapters.append(entry['Chapter Number'])
    return chapters
