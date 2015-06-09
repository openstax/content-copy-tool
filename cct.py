#!/usr/bin/python
import getopt
import sys
import re
import subprocess
import os
import util as util
import http_util as http
import content_util as cu
import create_module as cm
import create_workgroup as cw
import cnx_util as cnx
import cli as cli
import datetime
"""
This script is the main script of the content-copy-tool, it requires the
presence of the following utility files to execute properly.

util.py
content_util.py
http_util.py
cnx_util.py
create_module.py
create_workgroup.py
cli.py
"""

VERSION = 'OpenStaxCNX Content-Copy-Tool v.0.1'
PRODUCTION = False

def run(settings, input_file, workgroups, dryrun, copy, chapters, roles, publish, selenium):
    config = util.parse_input(settings)

    chapter_number_column = str(config['chapter_number_column'])
    chapter_title_column = str(config['chapter_title_column'])
    module_title_column = str(config['module_title_column'])
    module_ID_column = str(config['module_ID_column'])

    bookmap, placeholders = cu.read_csv(input_file)
    booktitle = cu.parse_book_title(input_file)

    source_server = str(config['source_server'])
    destination_server = str(config['destination_server'])
    # ensure server addresses have 'http[s]://' prepended
    if not re.match('https?://', source_server):
        source_server = 'http://' + source_server
    if not re.match('https?://', destination_server):
        destination_server = 'http://' + destination_server
    credentials = str(config['credentials'])
    logfile = config['logfile']
    logger = util.init_logger(logfile)

    if placeholders:
        cu.remove_invalid_modules(bookmap, module_title_column)
        cu.strip_section_numbers(bookmap, module_title_column)
        if copy:
            # Confirm each entry in the bookmap has a source module ID.
            for module in bookmap:
                if module[module_ID_column] is '' or module[module_ID_column] is ' ':
                    logger.warn("\033[91mInput file has missing module IDs, content-copy map may be incomplete.\033[0m")
        if not chapters:
            # if the user does not specify, use all of the chapters
            chapters = cu.get_chapters(bookmap, chapter_number_column)

    # Check before you run
    user_confirm(logger, source_server, destination_server, credentials, booktitle, \
        placeholders, chapters, workgroups, copy, publish, dryrun)

    if placeholders:
        new_modules, output = create_placeholders(logger, workgroups, chapters, bookmap, booktitle, \
            destination_server, credentials, dryrun, selenium, chapter_number_column, chapter_title_column, module_title_column, module_ID_column)
    else:
        new_modules = bookmap

    if copy:
        # run_transfer_script(source_server, credentials, output) # bash version
        copy_content(source_server, config, new_modules, roles, logger, dryrun) # python version
    if placeholders:
        print 'See created copy map: \033[92m'+output+'\033[0m'

    if publish:
        for module in new_modules:
            logger.info("Publishing module: " + module[1])
            if not dryrun:
                id = cnx.publish_module(module[0] + '/' + module[1] + '/', credentials, False)
            # auth = tuple(credentials.split(':'))
            # headers = {"In-Progress": "false"}
            # data = {"message": "copied content"}
            # response = http.http_post_request(source_server+'/content/'+module[1]+'latest/sword', headers=headers, data=data, auth=auth)
            # print response.status_code, response.reason

    logger.info("------- Process completed --------")

def create_placeholders(logger, workgroups, chapters, bookmap, booktitle, destination_server, \
    credentials, dryrun, selenium, chapter_number_column, chapter_title_column, module_title_column, module_ID_column):
    """
    Creates placeholder workgroups and modules. This function will write out to
    file the content copy map.

    Arguments:
      logger                - the tool's logger.
      workgroups            - a boolean flag, if True: it will create workgroups
                              for the modules, if False: it will create modules
                              in personal workspace.
      chapters              - a list of chapter numbers (strings) for which
                              placeholders will be created. If the workgroups
                              flag is True, a workgroup will be created for each
                              chapter in this list.
      bookmap               - the list of data that determines what to create
                              placeholders for. This will be a parsed version of
                              the csv/tsv input file.
      booktitle             - the title of the book (or content), this is used
                              in naming schemes.
      destination_server    - the server on which the placeholders will be
                              created.
      credentials           - the user's username:password for the
                              destination_server.
      dryrun                - a boolean flag, if True, it will step through the
                              inputs, but not actually create any content.
      selenium              - a boolean flag, if True, it will use selenium for
                              content creation, if False, it will use http
                              requests.
      chapter_number_column - the title of the chapter number column in the
                              csv/tsv input file
      chapter_title_column  - the title of the chapter title column in the
                              csv/tsv input file
      module_title_column   - the title of the module title column in the
                              csv/tsv input file
      module_ID_column      - the title of the module ID column in the csv/tsv
                              input file

    Returns:
        A tuple of the new module information, and the name of the copy map
        file. The new module information is a list of entries, where each entry
        is a list of three elements:
        [destination workspace url], [destination module id], [source_module_id]
        Note: if the csv/tsv input file does not have source module ID's neither
        the output file or the new modules list will have source module ID's in them.
    """
    if workgroups:
        # Create a workgroup for each chapter
        logger.info("-------- Creating workgroups ------------------------")
        chapter_to_workgroup = {}
        wc = cw.WorkgroupCreator(logger) # selenium
        for chapter in chapters:
            wgtitle = booktitle+' - '+ cu.get_chapter_number_and_title(bookmap, chapter, chapter_number_column, chapter_title_column)+str(datetime.datetime.now())
            if selenium:
                wgid = wc.run_create_workgroup(wgtitle, destination_server, credentials, dryrun=dryrun)
            else:
                wgid = cnx.run_create_workgroup(wgtitle, destination_server, credentials, logger, dryrun=dryrun)
            if wgid is 'FAIL' or not re.match('wg[0-9]+', wgid):
                logger.error("Workgroup " + wgtitle + " failed to be created, skipping chapter " + chapter)
                chapters.remove(chapter)
            chapter_to_workgroup[chapter] = destination_server + '/GroupWorkspaces/' + wgid

    logger.info("-------- Creating modules -------------------------------")
    # Create each module
    new_modules = []
    mc = cm.ModuleCreator(logger)
    moduleID = ''
    for module in bookmap:
        args = []
        if module[chapter_number_column] in chapters:
            workgroup_url = 'Members/'
            if workgroups:
                workgroup_url = chapter_to_workgroup[module[chapter_number_column]]

            if selenium:
                moduleID = mc.run_create_and_publish_module(module[module_title_column], destination_server, credentials, workgroup_url, dryrun=dryrun) # selenium version
            else:
                moduleID = cnx.run_create_and_publish_module(module[module_title_column], destination_server, credentials, logger, workgroup_url, dryrun=dryrun) # http version

            # bookkeeping for later
            if workgroups:
                args.append(chapter_to_workgroup[module[chapter_number_column]])
            args.append(moduleID)
            if module[module_ID_column] is not '':
                args.append(module[module_ID_column])
            util.record_creation(new_modules, args)

    output = util.write_list_to_file(new_modules, booktitle)
    return new_modules, output

def run_transfer_script(source, credentials, content_copy_map):
    """ Runs the bash transfer script """
    subprocess.call("sh transfer_user.sh -f "+source+" -u "+credentials+" \'"+content_copy_map+"\'", shell=True)

def copy_content(source, config, content_copy_map, roles, logger, dryrun):
    """
    Copies content from source server to server specified by each entry in the
    content copy map.

    Arguments:
      source           - the source server to copy the content from, (may or may
                         not have 'http://' prepended)
      config           - the configuration from the settings file
      content_copy_map - a list of triples containing an entry for each module
                         to copy, format is:
        '[destination workgroup url] [destination module ID] [source module ID]'
      roles            - a boolean flag to trigger the updating of roles or not,
                         TODO describe what updating roles will destination
      logger           - a reference to the tool's logger

    Returns:
      Nothing. It will, however, leave temporary & downloaded files for content
      that did not succeed in transfer.
    """
    credentials = str(config['credentials'])
    for entry in content_copy_map:
        try:
            source_moduleID = entry[2].strip('\n')
            destination_moduleID = entry[1]
            destination_workgroup = entry[0]
        except IndexError:
            logger.error("\033[91mFailure reading content for module, skipping.\033[0m")
            continue
        files = []
        logger.info("Copying content for module: "+source_moduleID)
        if not dryrun:
            files.append(http.http_download_file(source+'/content/'+source_moduleID+'/latest/module_export?format=zip', source_moduleID, '.zip'))
            files.append(http.http_download_file(source+'/content/'+source_moduleID+'/latest/rhaptos-deposit-receipt', source_moduleID, '.xml'))
            if roles:
                replace_map = cu.prepare_role_updates(source_moduleID+'.xml', config)
                cu.update_roles(source_moduleID+'.xml', replace_map)

            # remove index.cnxml.html from zipfile
            dir = util.extract_zip(source_moduleID+'.zip')
            os.remove(source_moduleID+'.zip')
            zipdir = os.path.dirname(os.path.realpath(__file__))+'/'+dir
            util.remove_file_from_dir(zipdir, 'index.cnxml.html')
            util.zipdir(zipdir, source_moduleID+'.zip')

            res, mpart = http.http_upload_file(source_moduleID+'.xml',source_moduleID+'.zip', destination_workgroup+"/"+destination_moduleID+'/sword', credentials)
            files.append(mpart)
            # clean up temp files
            if res.status < 400:
                for file in files:
                    os.remove(file)
            else:
                print res.status, res.reason # TODO better handle for production

def user_confirm(logger, source_server, destination_server, credentials, booktitle, placeholders, chapters, workgroups, copy, publish, dryrun):
    """
    Prints a summary of the settings for the process that is about to run and
    asks for user confirmation.
    """
    logger.info("-------- Summary ---------------------------------------")
    logger.info("Source: \033[95m"+source_server+"\033[0m - Content will be copied from this server")
    logger.info("Destination: \033[95m"+destination_server+"\033[0m - Content will be created on this server")
    if PRODUCTION:
        logger.info("User: \033[95m"+credentials.split(':')[0]+"\033[0m")
    else:
        logger.info("Credentials: \033[95m"+credentials+"\033[0m")
    logger.info("Content: \033[95m"+booktitle+"\033[0m")
    logger.info("Chapters: \033[95m"+str(chapters)+"\033[0m")
    logger.info("Create placeholders?: \033[95m"+str(placeholders)+"\033[0m")
    if placeholders:
        logger.info("Create workgroups? \033[95m"+str(workgroups)+"\033[0m")
    logger.info("Copy content? \033[95m"+str(copy)+"\033[0m")
    logger.info("Publish content? \033[95m"+str(publish)+"\033[0m")
    if dryrun:
        logger.info("------------NOTE: \033[95mDRY RUN\033[0m-----------------")

    while True:
        var = raw_input("\33[95mPlease verify this information. If there are warnings, consider checking your data.\nEnter:\n    \033[92m1\033[0m - Proceed\n    \033[91m2\033[0m - Cancel\n>>> ")
        if var is '1':
            break
        elif var is '2':
            sys.exit()

def main():
    parser = cli.get_parser(VERSION)
    args = parser.parse_args()
    cli.verify_args(args)

    if args.chapters:
        args.chapters.sort()
    run(args.settings, args.input_file, args.workgroups, args.dryrun, args.copy, args.chapters, args.roles, args.publish, args.selenium)

if __name__ == "__main__":
    main()
