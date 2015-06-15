# Configuration Objects
class CopyConfiguration:
    def __init__(self, source_server, destination_server, credentials):
        self.source_server = source_server
        self.destination_server = destination_server
        self.credentials = credentials


class BookmapConfiguration:
    """ Object that holds the bookmap configuration: the column names """
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


class RunOptions:
    def __init__(self, workgroups, copy, roles, accept_roles, publish, chapters, dryrun, selenium=False):
        self.workgroups = workgroups
        self.copy = copy
        self.roles = roles
        self.accept_roles = accept_roles
        self.publish = publish
        self.chapters = chapters
        self.dryrun = dryrun
        self.selenium = selenium


class RoleConfiguration:
    def __init__(self, creators, maintainers, rightholders):
        self.creators = creators
        self.maintainers = maintainers
        self.rightholders = rightholders


class RunConfiguration:
    def __init__(self, settings, input, logger, run_options, copy_config, bookmap_config):
        self.settings = settings
        self.input_file = input
        self.logger = logger
        self.run_options = run_options
        self.copy_config = copy_config
        self.bookmap_config = bookmap_config
