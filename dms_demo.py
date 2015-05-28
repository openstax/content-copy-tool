#!/usr/bin/python
import getopt
import sys
import re
import util as util
import content_util as cu
import create_module as cm
import create_workgroup as cw

VERSION = 'OpenStaxCNX Content-Copy-Tool v.0.1'

def run(settings, input_file, workgroups, dryrun, copy, chapters):
    config = util.parse_input(settings)
    bookmap = cu.read_csv(input_file)
    cu.remove_invalid_modules(bookmap)
    cu.strip_section_numbers(bookmap)
    booktitle = cu.parse_book_title(input_file)

    server = str(config['destination_server'])
    credentials = str(config['credentials'])
    logfile = config['logfile']
    logger = util.init_logger(logfile)

    if not chapters:
        chapters = cu.get_chapters(bookmap)

    if workgroups:
        # Create a workgroup for each chapter
        logger.info("---------Creating workgroups---------------------------------")
        chapter_to_workgroup = {}
        wc = cw.WorkgroupCreator(logger)
        for chapter in chapters:
            wgid = wc.run_create_workgroup(booktitle+' - '+cu.get_chapter_number_and_title(bookmap, chapter), \
                server, credentials, dryrun=dryrun)
            if not re.match('http', server):
                server = 'http://'+server
            chapter_to_workgroup[chapter] = server+'/GroupWorkspaces/'+wgid

    logger.info("---------Creating modules------------------------------------")
    # Create each module
    mc = cm.ModuleCreator(logger)
    new_modules = []
    moduleID = ''
    for module in bookmap:
        args = []
        if module['Chapter Number'] in chapters:
            if workgroups:
                moduleID = mc.run_create_and_publish_module(module['Module Title'], \
                    server, credentials, \
                    chapter_to_workgroup[module['Chapter Number']], dryrun=dryrun)
                args.append(chapter_to_workgroup[module['Chapter Number']])
            else:
                moduleID = mc.run_create_and_publish_module(module['Module Title'], \
                    server, credentials, dryrun=dryrun)
            args.append(moduleID)
            if module['Module ID'] is not '':
                args.append(module['Module ID'])
            util.record_creation(new_modules, args)

    # logger.info("Created these new modules: "+str(new_modules))

    if copy:
        output = util.write_list_to_file(new_modules, booktitle)
        print 'See generated migration map: \033[92m'+output+'\033[0m'
        print '...\nNext Steps: run the transfer scripts - Feature not implemented.'

    logger.info("---- Process completed --------")

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvs:i:p:wdc", ["help", "version", "settings=","input-file=","chapters=", "workgroups", "dryrun", "copy"])
    except getopt.GetoptError as err:
        print str(err)
        usage()
        sys.exit(2)
    workgroups = False
    dryrun = False
    copy = False
    settings = None
    input_file = None
    chapters = []
    for o, a in opts:
        if o == "-w":
            workgroups = True
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-s", "--settings"):
            settings = str(a)
        elif o in ("-i", "--input-file"):
            input_file = str(a)
        elif o in ("-p", "--chapters"):
            chapters.append(a)
        elif o in ("-d", "--dryrun"):
            dryrun = True
        elif o in ("-c", "--copy"):
            copy = True
        elif o in ("-v", "--version"):
            print VERSION
            sys.exit()
        else:
            print("ERROR: unhandled option: "+o+' '+a)
            sys.exit()

    if not settings or not input_file:
        print("ERROR - bad input: must have a settings file (-s) and input_file (-i). Use -h or --help for usage")
        sys.exit()

    chapters.sort()
    run(settings, input_file, workgroups, dryrun, copy, chapters)

def usage():
    usage = """
    This script copies a set of modules from one server to another, creating workgroups if desired.

    OPTIONS:
        -h, --help                                      Show this message
        -v, --version                                   Prints the tool's version
        -s, --settings [filepath]                       Settings file path
        -w, --workgroups                                Create workgroups for chapter titles (optional - must have chapter titles if enabled)
        -i, --input-file [filepath]                     The input file path
        -p, --chapters [chapters numbers to copy]       Which chapters to copy (optional)
        -d, --dryrun                                    Steps through input processing, but does NOT create or copy any content.
                                                        This is used for checking input file correctness (optional)
        -c, --copy                                      Will copy the data from source server to destination server. Without this flag,
                                                        the placeholder modules will be created, but no content will be copied over.
                                                        When using this flag, input file must have a 'Module ID' column filled for each
                                                        module that will be copied.

    The input file should be in the following form:

    Chapter Number,Chapter Title,Module Title,Module ID
    5,History of Rice University,5.1 The Founding of the Institution,m53341

    and the title of the file should be [the title of the book].csv
    The Module ID is only required if the -c, --copy flag is set (if you
    want to copy content to another server)

    Example usage:
    ./dms_demo.py -s settings.json -i Psychology.csv -c 0 1 2 3 -wt

    This will copy chapters 0, 1, 2, and 3 from the Psychology book according to the csv file, creating workgroups for each chapter, and
    to the server described by settings.json

    Currently, the script will generate the migration map file if the copy flag is set.
    """
    print '    '+VERSION
    print usage

if __name__ == "__main__":
    main()
