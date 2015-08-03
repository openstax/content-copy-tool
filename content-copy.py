#!/usr/bin/python
import sys
import traceback
import lib.util as util
import lib.command_line_interface as cli
from lib.operation_objects import *
from lib.bookmap import *
from lib.role_updates import *
import subprocess
import signal
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

VERSION = 'OpenStaxCNX Content-Copy-Tool v.1.2'
PRODUCTION = True


def run(settings, input_file, run_options):
    try:
        config = util.parse_json(settings)
    except Exception, e:
        print("There was an error reading the settings file: %s, confirm that the formatting compiles with "
                     "all json standards." % settings)
        print(traceback.format_exc())
        print("There was an error reading the settings file: %s, confirm that the formatting compiles with "
                     "all json standards." % settings)
        sys.exit(1)

    logfile = config['logfile']
    logger = util.init_logger(logfile)
    logger.debug("Logger is up and running.")

    # Bookmap
    bookmap_config = BookmapConfiguration(str(config['chapter_number_column']),
                                          str(config['chapter_title_column']),
                                          str(config['module_title_column']),
                                          str(config['source_module_ID_column']),
                                          str(config['destination_module_ID_column']),
                                          str(config['destination_workgroup_column']),
                                          str(config['unit_number_column']),
                                          str(config['unit_title_column']),
                                          str(config['strip_section_numbers']))
    logger.debug("Bookmap configuration has been created")
    bookmap = Bookmap(input_file, bookmap_config, run_options, logger)
    logger.debug("Bookmap has been created")

    # Copy Configuration and Copier
    source_server = str(config['source_server'])
    destination_server = str(config['destination_server'])
    # ensure server addresses have 'http[s]://' prepended
    if not regex.match(r'https?://', source_server):
        source_server = "http://%s" % source_server
    if not regex.match(r'https?://', destination_server):
        destination_server = "http://%s" % destination_server
    credentials = str(config['destination_credentials'])
    copy_config = CopyConfiguration(source_server, destination_server, credentials)
    copier = Copier(copy_config, bookmap.bookmap, str(config['path_to_tool']))
    logger.debug("Copier has been created")
    # Role Configuration
    role_config = RoleConfiguration(list(config['authors']),
                                    list(config['maintainers']),
                                    list(config['rightsholders']), config, credentials)
    logger.debug("Role configuration has been created.")
    # Content_creator
    content_creator = ContentCreator(destination_server, credentials)
    logger.debug("ContentCreator has been created.")
    failures = []

    user_confirm(logger, copy_config, bookmap, run_options, role_config)  # Check before you run

    try:
        logger.debug("Beginning processing.")
        if run_options.modules or run_options.workgroups:  # create placeholders
            create_placeholders(logger, bookmap, copy_config, run_options, content_creator, failures)
            output = bookmap.save(run_options.units)  # save output data
            logger.debug("Finished created placeholders, output has been saved: %s." % output)
        if run_options.copy:  # copy content
            copier.copy_content(role_config, run_options, logger, failures)
            logger.debug("Finished copying content.")
        if run_options.accept_roles and not run_options.dryrun:  # accept all pending role requests
            RoleUpdater(role_config).accept_roles(copy_config, logger, failures)
            logger.debug("Finished updating roles.")
        if run_options.collections:  # create and populate the collection
            create_populate_and_publish_collection(content_creator, copy_config, bookmap, run_options.units,
                                                   run_options.publish_collection, run_options.dryrun, logger, failures)
            logger.debug("Finished creating and populating the collection.")
        if run_options.publish:  # publish the modules
            publish_modules_post_copy(copier, content_creator, run_options, credentials, logger, failures)
            logger.debug("Finished publishing modules.")
    except (CCTError, util.TerminateError, util.SkipSignal) as e:
        output = bookmap.save(run_options.units, True)
        logger.error(e.msg)

    if run_options.modules or run_options.workgroups:
        logger.info("See output: \033[95m%s\033[0m" % output)
    print_failures(logger, failures)
    logger.info("------- Process completed --------")
    return bookmap.booktitle


def create_placeholders(logger, bookmap, copy_config, run_options, content_creator, failures):
    """
    Creates placeholder modules on the destination server (and workgroups if enables).

    Arguments:
        logger - the tool's logger
        bookmap - the bookmap of the input data parsed from the input file
        copy_config - the configuration of the copier with source and destination urls and credentials
        run_options - the input running options, what the tool should be doing
        content_creator - the content creator object
        failures - the list of failures to track failed placeholder creations

    Returns:
        None
    """
    if run_options.workgroups:
        logger.info("-------- Creating workgroups ------------------------")
        chapter_to_workgroup = {}
        workgroups_to_remove = []
        for workgroup in bookmap.bookmap.workgroups:
            try:
                content_creator.run_create_workgroup(workgroup, copy_config.destination_server, copy_config.credentials,
                                                     logger, dryrun=run_options.dryrun)
                logger.debug("[CREATED WORKGROUP] %s - %s" % (workgroup.title, workgroup.url))
            except util.TerminateError:
                raise util.TerminateError("Terminate Signaled")
            except (CCTError, util.SkipSignal, Exception) as e:
                if type(e) is not CCTError and type(e) is not util.SkipSignal:
                    logger.error("Problematic Error")
                    logger.debug(traceback.format_exc())
                if type(e) is util.SkipSignal:
                    logger.warn("User skipped creating workgroup.")
                logger.error("Workgroup %s failed to be created, skipping chapter %s" %
                             (workgroup.title, workgroup.chapter_number))
                workgroups_to_remove.append((workgroup, workgroup.chapter_number))
                for module in bookmap.bookmap.modules:
                    if module.chapter_number is workgroup.chapter_number:
                        module.valid = False
                        failures.append((module.full_title(), " creating placeholder"))
            chapter_to_workgroup[workgroup.chapter_number] = workgroup

        for workgroup, chapter in workgroups_to_remove:
            bookmap.chapters.remove(chapter)
            bookmap.bookmap.workgroups.remove(workgroup)

        logger.debug("Operating on these chapters now: %s" % bookmap.chapters)

    logger.info("-------- Creating modules -------------------------------")
    for module in bookmap.bookmap.modules:
        if module.valid and module.chapter_number in bookmap.chapters:
            workgroup_url = 'Members/'
            if run_options.workgroups:
                workgroup_url = chapter_to_workgroup[module.chapter_number].url
            if module.destination_workspace_url != "" and module.destination_workspace_url is not None:
                logger.debug("Adding module %s to existing workgroup %s" %
                             (module.title, module.destination_workspace_url))
                workgroup_url = module.destination_workspace_url
            try:
                content_creator.run_create_and_publish_module(module, copy_config.destination_server, 
                                                              copy_config.credentials, logger, workgroup_url, 
                                                              dryrun=run_options.dryrun)
                if run_options.workgroups:
                    chapter_to_workgroup[module.chapter_number].add_module(module)
                    chapter_to_workgroup[module.chapter_number].unit_number = module.unit_number
                logger.debug("[CREATED MODULE] %s - %s" % (module.title, module.destination_id))
            except util.TerminateError:
                raise util.TerminateError("Terminate Signaled")
            except (CCTError, Exception) as e:
                if type(e) is not CCTError and type(e) is not util.SkipSignal:
                    logger.error("Problematic Error")
                    logger.debug(traceback.format_exc())
                if type(e) is util.SkipSignal:
                    logger.warn("User skipped creating module.")
                logger.error("Module %s failed to be created. " % module.title)
                module.valid = False
                failures.append((module.full_title(), " creating placeholder"))


def create_populate_and_publish_collection(content_creator, copy_config, bookmap, units, publish_collection, dry_run,
                                           logger, failures):
    collection = None
    if not dry_run:
        try:
            logger.debug("Creating collection.")
            collection = content_creator.create_collection(copy_config.credentials, bookmap.booktitle,
                                                           copy_config.destination_server, logger)
        except util.TerminateError:
            raise util.TerminateError("Terminate Signaled")
        except (CCTError, Exception) as e:
            if type(e) is not CCTError and type(e) is not util.SkipSignal:
                    logger.error("Problematic Error")
                    logger.debug(traceback.format_exc())
            if type(e) is util.SkipSignal:
                logger.warn("User skipped creating collection.")
            logger.error("Failed to create the collection")
            failures.append(("%s" % bookmap.booktitle, "creating collection"))
            return None
    unit_numbers_and_title = set()
    units_map = {}
    if units:
        for module in bookmap.bookmap.modules:
            if module.chapter_number in bookmap.chapters \
                    and module.unit_number != 'APPENDIX' \
                    and module.unit_number != "":
                unit_numbers_and_title.add((module.unit_number, module.unit_title))
        as_list = list(unit_numbers_and_title)
        as_list.sort(key=lambda unit_number_and_title: unit_number_and_title[0])
        if not dry_run:
            for unit_number, unit_title in as_list:
                try:
                    unit_collection = content_creator.add_subcollections(["Unit %s. %s" % (unit_number, unit_title)],
                                                                         copy_config.destination_server,
                                                                         copy_config.credentials, collection, logger)
                    units_map[unit_number] = unit_collection[0]
                except util.TerminateError:
                    raise util.TerminateError("Terminate Signaled")
                except (CCTError, Exception) as e:
                    if type(e) is not CCTError and type(e) is not util.SkipSignal:
                        logger.error("Problematic Error")
                        logger.debug(traceback.format_exc())
                    if type(e) is util.SkipSignal:
                        logger.warn("User skipped creating subcollections for units.")
                    logger.error("Failed to create subcollections for units")
                    failures.append(("%s" % unit_number,
                                     "creating unit subcollections (those chapters were added to the collection %s)" %
                                     collection.title))
                    units_map[unit_number] = collection
    for workgroup in bookmap.bookmap.workgroups:
        if workgroup.chapter_number in bookmap.chapters:
            logger.debug("Added subcollections and modules to collection.")
            parent = collection
            if not dry_run:
                if units and workgroup.chapter_number != '0' \
                         and workgroup.unit_number != 'APPENDIX' \
                         and workgroup.unit_number != "":
                    parent = units_map[workgroup.unit_number]
                try:
                    if ((units and workgroup.unit_number != 'APPENDIX' and workgroup.unit_number != "") or not units)\
                            and workgroup.chapter_number != '0':
                        subcollections = content_creator.add_subcollections([workgroup.chapter_title],
                                                                            copy_config.destination_server,
                                                                            copy_config.credentials,
                                                                            parent, logger)
                        module_parent = subcollections[0]
                    else:
                        module_parent = collection
                except util.TerminateError:
                    raise util.TerminateError("Terminate Signaled")
                except (CCTError, Exception) as e:
                    if type(e) is not CCTError and type(e) is not util.SkipSignal:
                        logger.error("Problematic Error")
                        logger.debug(traceback.format_exc())
                    if type(e) is util.SkipSignal:
                        logger.warn("User skipped creating subcollections for chapters.")
                    logger.error("Failed to create subcollections for chapter %s, adding modules to %s" %
                                 (workgroup.chapter_number, collection.title))
                    failures.append(("%s" % workgroup.chapter_title,
                                     "creating subcollections (those modules were added to collection %s)" %
                                     collection.title))
                    module_parent = collection
                try:
                    content_creator.add_modules_to_collection(workgroup.modules, copy_config.destination_server,
                                                              copy_config.credentials, module_parent, logger, failures)

                except util.TerminateError:
                    raise util.TerminateError("Terminate Signaled")
                except (CCTError, Exception) as e:
                    if type(e) is not CCTError and type(e) is not util.SkipSignal:
                        logger.error("Problematic Error")
                        logger.debug(traceback.format_exc())
                    if type(e) is util.SkipSignal:
                        logger.warn("User skipped adding modules to subcollection.")
                    logger.error("Failed to add modules to chapter %s" % workgroup.chapter_number)
                    failures.append(("%s" % workgroup.modules, "adding modules to subcollections"))

    if not dry_run and publish_collection:
        try:
            content_creator.publish_collection(copy_config.destination_server, copy_config.credentials, collection,
                                               logger)

        except util.TerminateError:
            raise util.TerminateError("Terminate Signaled")
        except (CCTError, Exception) as e:
            if type(e) is not CCTError and type(e) is not util.SkipSignal:
                logger.error("Problematic Error")
                logger.debug(traceback.format_exc())
            if type(e) is util.SkipSignal:
                logger.warn("User skipped publishing collection.")
            logger.error("Failed to publish collection")
            failures.append(("%s" % collection.title, "publishing collection"))
            return None


def publish_modules_post_copy(copier, content_creator, run_options, credentials, logger, failures):
    """
    Publishes modules that has been copied to the destination server.

    Arguments:
        copier - the copier object that did the copying
        content_creator - the creator object to do the publishing
        run_options - the input running options, what will the tool do
        credentials - the user's credentials
        logger - the tool's logger
        failures - the working list of failures

    Returns:
        None
    """
    for module in copier.copy_map.modules:
        if module.valid and module.chapter_number in run_options.chapters:
            logger.info("Publishing module: %s - %s" % (module.destination_id, module.full_title()))
            if not run_options.dryrun:
                try:
                    content_creator.publish_module("%s/%s/" % (module.destination_workspace_url, module.destination_id),
                                                   credentials, logger, False)
                except util.TerminateError:
                    raise util.TerminateError("Terminate Signaled")
                except (CCTError, Exception) as e:
                    if type(e) is not CCTError and type(e) is not util.SkipSignal:
                        logger.error("Problematic Error")
                        logger.debug(traceback.format_exc())
                    if type(e) is util.SkipSignal:
                        logger.warn("User skipped publishing module.")
                    logger.error("Failed to publish module %s", module.destination_id)
                    module.valid = False
                    failures.append((module.full_title(), "publishing module"))


def print_failures(logger, failures):
    for failure in failures:
        logger.error("\033[95mFailed %s - \033[91m%s\033[0m", failure[1], failure[0])


def user_confirm(logger, copy_config, bookmap, run_options, role_config):
    """
    Prints a summary of the settings for the process that is about to run and
    asks for user confirmation.
    """
    logger.info("-------- Summary ---------------------------------------")
    if run_options.copy:  # confirm each entry in the bookmap has a source module ID.
        last_title = "!ITS THE FIRST ONE!"
        for module in bookmap.bookmap.modules:
            if module.chapter_number in bookmap.chapters and (module.source_id is '' or module.source_id is ' ' or
                                                              module.source_id is None):
                logger.warn("\033[91mInput file has missing source module ID for module [%s]"
                            "- the module after [%s].\033[0m" % (module.title, last_title))
            last_title = module.title
    logger.info("Source: \033[95m%s\033[0m" % copy_config.source_server)
    logger.info("Destination: \033[95m%s\033[0m" % copy_config.destination_server)
    if PRODUCTION:
        logger.info("User: \033[95m%s\033[0m" % copy_config.credentials.split(':')[0])
    else:
        logger.info("Destination Credentials: \033[95m%s\033[0m" % copy_config.credentials)
    logger.info("Content: \033[95m%s\033[0m" % bookmap.booktitle)
    logger.info("Which Chapters: \033[95m%s\033[0m" % ', '.join(bookmap.chapters))
    logger.info("Number of Modules: \033[95m%s\033[0m" %
                len([module for module in bookmap.bookmap.modules if module.chapter_number in bookmap.chapters]))
    logger.info("Create placeholders?: \033[95m%s\033[0m" % run_options.modules or run_options.workgroups)
    if run_options.modules:
        logger.info("Create workgroups? \033[95m%s\033[0m" % run_options.workgroups)
    logger.info("Copy content? \033[95m%s\033[0m" % run_options.copy)
    if run_options.copy:
        logger.info("Edit roles? \033[95m%s\033[0m" % run_options.roles)
    if run_options.accept_roles:
        logger.info("Accept roles? \033[95m%s\033[0m" % run_options.accept_roles)
    if run_options.roles or run_options.accept_roles:
            logger.info("Authors: \033[95m%s\033[0m" % ', '.join(role_config.creators))
            logger.info("Maintainers: \033[95m%s\033[0m" % ', '.join(role_config.maintainers))
            logger.info("Rightsholders: \033[95m%s\033[0m" % ', '.join(role_config.rightholders))
    logger.info("Create collections? \033[95m%s\033[0m" % run_options.collections)
    if run_options.collections:
        logger.info("Units? \033[95m%s\033[0m" % run_options.units)
    logger.info("Publish content? \033[95m%s\033[0m" % run_options.publish)
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
    run_options = RunOptions(args.modules, args.workgroups, args.copy, args.roles, args.accept_roles, args.collection,
                             args.units, args.publish, args.publish_collection, args.chapters, args.exclude,
                             args.dryrun)
    booktitle = ""
    signal.signal(signal.SIGINT, util.handle_terminate)
    signal.signal(signal.SIGTSTP, util.handle_user_skip)
    try:
        booktitle = run(args.settings, args.input_file, run_options)
    except Exception, e:
        print "Error: %s", e
        print(traceback.format_exc())
    app = '"Terminal"'
    msg = '"Content Copy for '+booktitle+' has completed, see Terminal for results."'
    bashCommand = "echo; osascript -e 'tell application "+app+"' -e 'activate' -e 'display alert "+msg+"' -e 'end tell'"
    subprocess.call([bashCommand], shell=True)

if __name__ == "__main__":
    main()
