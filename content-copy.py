#!/usr/bin/python
import getopt
import sys
import re
import subprocess
import os
import util as util
import http_util as http
import create_module as cm
import create_workgroup as cw
# import cnx_util as cnx
import command_line_interface as cli
from objects import *
import datetime
from configurations import *
"""
This script is the main script of the content-copy-tool, it requires the
presence of the following utility files to execute properly.

util.py
http_util.py
cnx_util.py
create_module.py
create_workgroup.py
command_line_interface.py
"""

VERSION = 'OpenStaxCNX Content-Copy-Tool v.0.2'
PRODUCTION = False

def run(settings, input_file, run_options):
    config = util.parse_json(settings)

    bookmap_config = BookmapConfiguration(str(config['chapter_number_column']),
                                          str(config['chapter_title_column']),
                                          str(config['module_title_column']),
                                          str(config['source_module_ID_column']),
                                          str(config['source_workgroup_column']),
                                          str(config['destination_module_ID_column']),
                                          str(config['destination_workgroup_column']),
                                          str(config['strip_section_numbers']))
    bookmap = Bookmap(input_file, bookmap_config, run_options.chapters, run_options.workgroups)
    run_options.placeholders = bookmap.placeholders # if False, input_file is a .out (copy map)

    # Copy Configuration
    source_server = str(config['source_server'])
    destination_server = str(config['destination_server'])
    # ensure server addresses have 'http[s]://' prepended
    if not re.match('https?://', source_server):
        source_server = 'http://' + source_server
    if not re.match('https?://', destination_server):
        destination_server = 'http://' + destination_server
    credentials = str(config['credentials'])

    copy_config = CopyConfiguration(source_server, destination_server, credentials)

    role_config = RoleConfiguration(list(config['creators']), list(config['maintainers']), list(config['rightholders']))

    content_creator = ContentCreator(destination_server, credentials)

    logfile = config['logfile']
    logger = util.init_logger(logfile)

    logger.info("-------- Summary ---------------------------------------")
    if run_options.placeholders: # confirm proper input
        if run_options.copy:
            # Confirm each entry in the bookmap has a source module ID.
            for module in bookmap.bookmap.modules:
                if module.source_id is '' or module.source_id is ' ':
                    logger.warn("\033[91mInput file has missing module IDs, content-copy map may be incomplete.\033[0m")
        if not run_options.chapters:
            # if the user does not specify, use all of the chapters
            run_options.chapters = bookmap.get_chapters()
    # else: # read in copy map
    #     copier = Copier(copy_config, file=input_file)

    # Check before you run
    user_confirm(logger, copy_config, bookmap.booktitle, run_options)

    if run_options.placeholders: # create placeholders
        new_modules, output = create_placeholders_objects(logger, bookmap, copy_config, run_options, content_creator)

    if run_options.copy: # copy content
        copier = Copier(copy_config, object=bookmap.bookmap)
        # run_transfer_script(source_server, credentials, output) # bash version
        copier.copy_content(role_config, run_options, logger)
    if run_options.accept_roles: # accept all pending role requests
        RoleUpdater().accept_roles(copy_config)
    if run_options.publish: # publish the modules
        for module in copier.copy_map.modules:
            logger.info("Publishing module: " + module.destination_id)
            if not run_options.dryrun:
                id, url = content_creator.publish_module(module.destination_workspace_url + '/' + module.destination_id + '/', credentials, False)
            # auth = tuple(credentials.split(':'))
            # headers = {"In-Progress": "false"}
            # data = {"message": "copied content"}
            # response = http.http_post_request(source_server+'/content/'+module[1]+'latest/sword', headers=headers, data=data, auth=auth)
            # print response.status_code, response.reason

    # save output data
    output = bookmap.save()
    logger.info("See output: \033[95m"+output+"\033[0m")
    logger.info("------- Process completed --------")

def create_placeholders(logger, bookmap, copy_config, run_options):
    """
    Creates placeholder workgroups and modules. This function will write out to
    file the content copy map.

    Arguments:
    TODO update docstring
      logger                - the tool's logger.
      bookmap               - the list of data that determines what to create
                              placeholders for. This will be a parsed version of
                              the csv/tsv input file.
      booktitle             - the title of the book (or content), this is used
                              in naming schemes.


    Returns:
        A tuple of the new module information, and the name of the copy map
        file. The new module information is a list of entries, where each entry
        is a list of three elements:
        [destination workspace url], [destination module id], [source_module_id]
        Note: if the csv/tsv input file does not have source module ID's neither
        the output file or the new modules list will have source module ID's in them.
    """
    if run_options.workgroups:
        # Create a workgroup for each chapter
        logger.info("-------- Creating workgroups ------------------------")
        chapter_to_workgroup = {}
        wc = cw.WorkgroupCreator(logger) # selenium
        for chapter in run_options.chapters:
            wgtitle = bookmap.booktitle+' - '+ bookmap.get_chapter_number_and_title(chapter)+str(datetime.datetime.now())
            if run_options.selenium:
                wgid = wc.run_create_workgroup(wgtitle, copy_config.destination_server, copy_config.credentials, dryrun=run_options.dryrun)
            else:
                wgid = cnx.run_create_workgroup(wgtitle, copy_config.destination_server, copy_config.credentials, logger, dryrun=run_options.dryrun)
            if wgid is 'FAIL' or not re.match('wg[0-9]+', wgid):
                logger.error("Workgroup " + wgtitle + " failed to be created, skipping chapter " + chapter)
                run_options.chapters.remove(chapter)
            chapter_to_workgroup[chapter] = copy_config.destination_server + '/GroupWorkspaces/' + wgid

    logger.info("-------- Creating modules -------------------------------")
    # Create each module
    new_modules = []
    mc = cm.ModuleCreator(logger)
    moduleID = ''
    for module in bookmap.bookmap:
        if module[bookmap.config.chapter_number_column] in run_options.chapters:
            workgroup_url = 'Members/'
            if run_options.workgroups:
                workgroup_url = chapter_to_workgroup[module[bookmap.config.chapter_number_column]]

            if run_options.selenium:
                moduleID = mc.run_create_and_publish_module(module[bookmap.config.module_title_column], copy_config.destination_server, copy_config.credentials, workgroup_url, dryrun=run_options.dryrun) # selenium version
            else:
                moduleID = cnx.run_create_and_publish_module(module[bookmap.config.module_title_column], copy_config.destination_server, copy_config.credentials, logger, workgroup_url, dryrun=run_options.dryrun) # http version

            # bookkeeping for later
            if run_options.workgroups:
                args.append(chapter_to_workgroup[module[bookmap.config.chapter_number_column]])
            args.append(moduleID)
            if module[bookmap.config.module_ID_column] is not '':
                args.append(module[bookmap.config.module_ID_column])
            Copier.record_creation(new_modules, args)

    output = Copier.write_list_to_file(new_modules, bookmap.booktitle)
    return new_modules, output

def create_placeholders_objects(logger, bookmap, copy_config, run_options, content_creator):
    if run_options.workgroups:
        logger.info("-------- Creating workgroups ------------------------")
        # workgroups = []
        chapter_to_workgroup = {}
        # for chapter in run_options.chapters:
        for workgroup in bookmap.bookmap.workgroups:
            # chapter_number_and_title = bookmap.get_chapter_number_and_title(chapter)
            # wgtitle = bookmap.booktitle+' - '+chapter_number_and_title+str(datetime.datetime.now())
            try:
                content_creator.run_create_workgroup(workgroup, copy_config.destination_server, copy_config.credentials, logger, dryrun=run_options.dryrun)
            except CustomError, error:
                logger.error("Workgroup " + workgroup.title + " failed to be created, skipping chapter " + workgroup.chapter_number)
                run_options.chapters.remove(workgroup.chapter_number)
                bookmap.bookmap.workgroups.remove(workgroup)
            # bookmap.bookmap.add_workgroup(new_workgroup)
            chapter_to_workgroup[workgroup.chapter_number] = workgroup

    logger.info("-------- Creating modules -------------------------------")
    modules = []
    for module in bookmap.bookmap.modules:
        if module.get_chapter_number() in run_options.chapters:
            workgroup_url = 'Members/'
            if run_options.workgroups:
                workgroup_url = chapter_to_workgroup[module.get_chapter_number()].url
            try:
                content_creator.run_create_and_publish_module(module, copy_config.destination_server, copy_config.credentials, logger, workgroup_url, dryrun=run_options.dryrun) # http version
                if run_options.workgroups:
                    chapter_to_workgroup[module.get_chapter_number()].add_module(module)
            except CustomError, error:
                logger.error("Module " + module.title + " failed to be created.")
            # modules.append(new_module)

    # bookmap.add_created_content(modules, run_options)
    # print bookmap.bookmap
    return None, ""


def run_transfer_script(source, credentials, content_copy_map):
    """ Runs the bash transfer script """
    subprocess.call("sh transfer_user.sh -f "+source+" -u "+credentials+" \'"+content_copy_map+"\'", shell=True)

def user_confirm(logger, copy_config, booktitle, run_options):
    """
    Prints a summary of the settings for the process that is about to run and
    asks for user confirmation.
    """
    logger.info("Source: \033[95m"+copy_config.source_server+"\033[0m - Content will be copied from this server")
    logger.info("Destination: \033[95m"+copy_config.destination_server+"\033[0m - Content will be created on this server")
    if PRODUCTION:
        logger.info("User: \033[95m"+copy_config.credentials.split(':')[0]+"\033[0m")
    else:
        logger.info("Credentials: \033[95m"+copy_config.credentials+"\033[0m")
    logger.info("Content: \033[95m"+booktitle+"\033[0m")
    logger.info("Chapters: \033[95m"+str(run_options.chapters)+"\033[0m")
    logger.info("Create placeholders?: \033[95m"+str(run_options.placeholders)+"\033[0m")
    if run_options.placeholders:
        logger.info("Create workgroups? \033[95m"+str(run_options.workgroups)+"\033[0m")
    logger.info("Copy content? \033[95m"+str(run_options.copy)+"\033[0m")
    if run_options.copy:
        logger.info("Edit roles? \033[95m"+str(run_options.roles)+"\033[0m")
    logger.info("Publish content? \033[95m"+str(run_options.publish)+"\033[0m")
    if run_options.dryrun:
        logger.info("------------NOTE: \033[95mDRY RUN\033[0m-----------------")

    while True:
        var = raw_input("\33[95mPlease verify this information. If there are \033[91mwarnings\033[95m, consider checking your data.\nEnter:\n    \033[92m1\033[0m - Proceed\n    \033[91m2\033[0m - Cancel\n>>> ")
        if var is '1':
            break
        elif var is '2':
            sys.exit()

def main():
    args = cli.get_parser(VERSION).parse_args()
    cli.verify_args(args)

    if args.chapters:
        args.chapters.sort()
    run_options = RunOptions(args.workgroups, args.copy, args.roles, args.accept_roles, args.publish, args.chapters, args.dryrun, args.selenium)
    run(args.settings, args.input_file, run_options)

if __name__ == "__main__":
    main()
