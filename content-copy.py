#!/usr/bin/python
import sys
import lib.util as util
import lib.command_line_interface as cli
from lib.operation_objects import *
from lib.bookmap import *
from lib.role_updates import *

"""
This script is the main script of the content-copy-tool, it requires the
presence of the following utility files to execute properly.

configuration_objects.py
operation_objects.py
bookmap.py
role_updates.py
util.py
http_util.py
command_line_interface.py
"""

VERSION = 'OpenStaxCNX Content-Copy-Tool v.0.3'
PRODUCTION = False

def run(settings, input_file, run_options):
    config = util.parse_json(settings)

    # Bookmap
    bookmap_config = BookmapConfiguration(str(config['chapter_number_column']),
                                          str(config['chapter_title_column']),
                                          str(config['module_title_column']),
                                          str(config['source_module_ID_column']),
                                          str(config['source_workgroup_column']),
                                          str(config['destination_module_ID_column']),
                                          str(config['destination_workgroup_column']),
                                          str(config['strip_section_numbers']))
    bookmap = Bookmap(input_file, bookmap_config, run_options)

    # Copy Configuration and Copier
    source_server = str(config['source_server'])
    destination_server = str(config['destination_server'])
    # ensure server addresses have 'http[s]://' prepended
    if not regex.match('https?://', source_server):
        source_server = 'https://' + source_server
    if not regex.match('https?://', destination_server):
        destination_server = 'https://' + destination_server
    credentials = str(config['credentials'])
    copy_config = CopyConfiguration(source_server, destination_server, credentials)
    copier = Copier(copy_config, bookmap.bookmap, str(config['path_to_tool']))

    # Role Configuration
    role_config = RoleConfiguration(list(config['authors']),
                                    list(config['maintainers']),
                                    list(config['rightsholders']), config, credentials)

    # Content_creator
    content_creator = ContentCreator(destination_server, credentials)

    logfile = config['logfile']
    logger = util.init_logger(logfile)

    user_confirm(logger, copy_config, bookmap, run_options, role_config)  # Check before you run

    try:
        if run_options.modules or run_options.workgroups:  # create placeholders
            create_placeholders(logger, bookmap, copy_config, run_options, content_creator)
        if run_options.copy:  # copy content
            copier.copy_content(role_config, run_options, logger)
        if run_options.accept_roles:  # accept all pending role requests
            RoleUpdater(role_config).accept_roles(copy_config)
        if run_options.publish:  # publish the modules
            publish_modules_post_copy(copier, content_creator, run_options, credentials, logger)
    except CCTError, e:
        logger.error(e.msg)

    if run_options.modules or run_options.workgroups:
        output = bookmap.save()  # save output data
        logger.info("See output: \033[95m" + output + "\033[0m")
    logger.info("------- Process completed --------")

def create_placeholders(logger, bookmap, copy_config, run_options, content_creator):
    """
    Creates placeholder modules on the destination server (and workgroups if enables).

    Arguments:
        logger - the tool's logger
        bookmap - the bookmap of the input data parsed from the input file
        copy_config - the configuration of the copier with source and destination urls and credentials
        run_options - the input running options, what the tool should be doing
        content_creator - the content creator object

    Returns:
        None
    """
    if run_options.workgroups:
        logger.info("-------- Creating workgroups ------------------------")
        chapter_to_workgroup = {}
        for workgroup in bookmap.bookmap.workgroups:
            try:
                content_creator.run_create_workgroup(workgroup, copy_config.destination_server, copy_config.credentials,
                                                     logger, dryrun=run_options.dryrun)
            except CCTError:
                logger.error("Workgroup " + workgroup.title + " failed to be created, skipping chapter " + 
                             workgroup.chapter_number)
                bookmap.chapters.remove(workgroup.chapter_number)
                bookmap.bookmap.workgroups.remove(workgroup)
            chapter_to_workgroup[workgroup.chapter_number] = workgroup

    logger.info("-------- Creating modules -------------------------------")
    for module in bookmap.bookmap.modules:
        if module.chapter_number in bookmap.chapters:
            workgroup_url = 'Members/'
            if run_options.workgroups:
                workgroup_url = chapter_to_workgroup[module.chapter_number].url
            try:
                content_creator.run_create_and_publish_module(module, copy_config.destination_server, 
                                                              copy_config.credentials, logger, workgroup_url, 
                                                              dryrun=run_options.dryrun)
                if run_options.workgroups:
                    chapter_to_workgroup[module.chapter_number].add_module(module)
            except CCTError:
                logger.error("Module " + module.title + " failed to be created.")

def publish_modules_post_copy(copier, content_creator, run_options, credentials, logger):
    """
    Publishes modules that has been copied to the destination server.

    Arguments:
        copier - the copier object that did the copying
        content_creator - the creator object to do the publishing
        run_options - the input running options, what will the tool do
        credentials - the user's credentials
        logger - the tool's logger

    Returns:
        None
    """
    for module in copier.copy_map.modules:
        if module.chapter_number in run_options.chapters:
            logger.info("Publishing module: " + module.destination_id)
            if not run_options.dryrun:
                content_creator.publish_module(module.destination_workspace_url + '/' + module.destination_id + '/', 
                                               credentials, False)

def user_confirm(logger, copy_config, bookmap, run_options, role_config):
    """
    Prints a summary of the settings for the process that is about to run and
    asks for user confirmation.
    """
    logger.info("-------- Summary ---------------------------------------")
    if run_options.copy:  # confirm each entry in the bookmap has a source module ID.
        for module in bookmap.bookmap.modules:
            if module.chapter_number in bookmap.chapters and (module.source_id is '' or module.source_id is ' ' or
                                                              module.source_id is None):
                logger.warn("\033[91mInput file has missing source module IDs.\033[0m")
    logger.info("Source: \033[95m" + copy_config.source_server + "\033[0m")
    logger.info("Destination: \033[95m" + copy_config.destination_server + "\033[0m")
    if PRODUCTION:
        logger.info("User: \033[95m" + copy_config.credentials.split(':')[0] + "\033[0m")
    else:
        logger.info("Credentials: \033[95m" + copy_config.credentials + "\033[0m")
    logger.info("Content: \033[95m" + bookmap.booktitle + "\033[0m")
    logger.info("Chapters: \033[95m" + ', '.join(bookmap.chapters) + "\033[0m")
    logger.info("Number of Modules: \033[95m" + 
                str(len([module for module in bookmap.bookmap.modules if module.chapter_number in bookmap.chapters])) + 
                "\033[0m")
    logger.info("Create placeholders?: \033[95m" + str(run_options.modules or run_options.workgroups) + "\033[0m")
    if run_options.modules:
        logger.info("Create workgroups? \033[95m" + str(run_options.workgroups) + "\033[0m")
    logger.info("Copy content? \033[95m" + str(run_options.copy) + "\033[0m")
    if run_options.copy:
        logger.info("Edit roles? \033[95m" + str(run_options.roles) + "\033[0m")
    if run_options.accept_roles:
        logger.info("Accept roles? \033[95m" + str(run_options.accept_roles) + "\033[0m")
    if run_options.roles or run_options.accept_roles:
            logger.info("Authors: \033[95m" + ', '.join(role_config.creators) + "\033[0m")
            logger.info("Maintainers: \033[95m" + ', '.join(role_config.maintainers) + "\033[0m")
            logger.info("Rightsholders: \033[95m" + ', '.join(role_config.rightholders) + "\033[0m")
    logger.info("Publish content? \033[95m" + str(run_options.publish) + "\033[0m")
    if run_options.dryrun:
        logger.info("------------NOTE: \033[95mDRY RUN\033[0m-----------------")

    while True:
        var = raw_input("\33[95mPlease verify this information. If there are \033[91mwarnings\033[95m, "
                        "consider checking your data.\n"
                        "Enter:\n"
                        "    \033[92m1\033[0m - Proceed\n"
                        "    \033[91m2\033[0m - Cancel\n>>> ")
        if var is '1':
            break
        elif var is '2':
            sys.exit()

def main():
    args = cli.get_parser(VERSION).parse_args()
    cli.verify_args(args)

    if args.chapters:
        args.chapters.sort()
    run_options = RunOptions(args.modules, args.workgroups, args.copy, args.roles, args.accept_roles, args.publish, 
                             args.chapters, args.exclude, args.dryrun)
    run(args.settings, args.input_file, run_options)

if __name__ == "__main__":
    main()
