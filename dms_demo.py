#!/usr/bin/python
import getopt
import sys
import re
import subprocess
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

    source_server = str(config['source_server'])
    destination_server = str(config['destination_server'])
    credentials = str(config['credentials'])
    logfile = config['logfile']
    logger = util.init_logger(logfile)

    if copy:
        for module in bookmap:
            if module['Module ID'] is '' or module['Module ID'] is ' ':
                logger.warn("Input file has missing module IDs, content-copy map may be incomplete")

    logger.info("-------- Summary ---------------------------------------")
    logger.info("Source: \033[92m"+source_server+"\033[0m - Content will be copied from this server")
    logger.info("Destination: \033[92m"+destination_server+"\033[0m - Content will be created on this server")
    logger.info("Credentials: \033[92m"+credentials+"\033[0m")
    logger.info("Content: \033[92m"+booktitle+"\033[0m")
    logger.info("Create workgroups? \033[92m"+str(workgroups)+"\033[0m")
    logger.info("Copy content? \033[92m"+str(copy)+"\033[0m")
    if dryrun:
        logger.info("Mode: \033[92mDRY RUN\033[0m")

    while True:
        var = raw_input("\33[95mPlease verify this information. If there are warnings, consider checking your data.\nEnter:\n    \033[92m1 - Proceed\n    \033[91m2 - Cancel\n\033[0m>>> ")
        if var is '1':
            break
        elif var is '2':
            sys.exit()

    if not chapters:
        chapters = cu.get_chapters(bookmap)

    if workgroups:
        # Create a workgroup for each chapter
        logger.info("-------- Creating workgroups --------------------------------")
        chapter_to_workgroup = {}
        wc = cw.WorkgroupCreator(logger)
        for chapter in chapters:
            wgid = wc.run_create_workgroup(booktitle+' - '+cu.get_chapter_number_and_title(bookmap, chapter), \
                destination_server, credentials, dryrun=dryrun)
            if not re.match('http', destination_server):
                destination_server = 'http://'+destination_server
            chapter_to_workgroup[chapter] = destination_server+'/GroupWorkspaces/'+wgid

    logger.info("-------- Creating modules -----------------------------------")
    # Create each module
    mc = cm.ModuleCreator(logger)
    new_modules = []
    moduleID = ''
    for module in bookmap:
        args = []
        if module['Chapter Number'] in chapters:
            if workgroups:
                moduleID = mc.run_create_and_publish_module(module['Module Title'], \
                    destination_server, credentials, \
                    chapter_to_workgroup[module['Chapter Number']], dryrun=dryrun)
            else:
                moduleID = mc.run_create_and_publish_module(module['Module Title'], \
                    destination_server, credentials, dryrun=dryrun)

            if copy and workgroups:
                args.append(chapter_to_workgroup[module['Chapter Number']])
            args.append(moduleID)
            if module['Module ID'] is not '' and copy:
                args.append(module['Module ID'])
            util.record_creation(new_modules, args)

    output = util.write_list_to_file(new_modules, booktitle)
    if copy:
        print 'See generated content-copy map: \033[92m'+output+'\033[0m'
        print '...\nNext Steps: run the transfer scripts - Feature not implemented yet.'
        # run_transfer_script(source_server, credentials, output)
    else:
        print 'See created module IDs: \033[92m'+output+'\033[0m'

    logger.info("------- Process completed --------")

def run_transfer_script(source, credentials, content_copy_map):
    subprocess.call("sh transfer_user.sh -f "+source+" -u "+credentials+" \'"+content_copy_map+"\'", shell=True)

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
    if not (copy and workgroups):
        print("ERROR - bad input: if you are copying content (-c), you need to create workgroups (-w) as well. Use -h or --help for usage")
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

    Currently, the script will generate the content-copy map file if the copy flag is set.
    """
    print '    '+VERSION
    print usage

if __name__ == "__main__":
    main()
