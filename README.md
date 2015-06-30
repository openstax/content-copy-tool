#Content Copy Tool

####Current Status
The content-copy-tool is currently in development. As of 6-9-15, the tool can create placeholder content, copy content, edit roles, and publish modules.

####TODO
- different credentials for source and destination - what will be source and destination
- name uniqueness: workspaces & modules
- config-ify license and url's and stuff

####Context
The Content-Copy-Tool is a python tool that provides configurable automation for copying content from one cnx server to another. The tool can create placeholder modules (and workgroups), copy content into those placeholders, edit the roles on the content during the copy, and publish\* modules. These can also be run independently\*\*.

\*\* Editing roles requires copying.

####Description
The Content-Copy-Tool is configurable. The first way of configuring it
is through the settings file (see usage below). The settings file must be saved
as a .json file. This file contains settings such as source and destination
servers, user credentials, and some other potentially dynamic information.

The second way to configure the tool is with the type of file provided as the
input file. If the input file is a .csv or .tsv file, the tool will
proceed to create placeholder modules on the destination server (other options
can modify this behavior some). If the input file is a .out file, the tool
will  not create placeholders, if the proper options are set (see below), it
will copy and/or publish the modules described in the input file.

The third way to configure the tool is through the control options. With these
options you can tell the tool to create workgroups for each chapter of content,
copy content from one server to another, modify roles on each module according
to the settings file, and/or publish the copied content. The other options
allow you to specify which chapters you want the tool to operate on and execute
a dry-run of the procedure. See below for examples.

The input file should be in the following form (commas can be replaced with tabs):

Chapter Number,Chapter Title,Module Title,Module ID
5,History of Rice University,5.1 The Founding of the Institution,m53341

and the title of the file should be [*the title of the book*].csv
Alternatively, the tool can accept a .tsv (tab separated values) file.
The Module ID is only required if the -c, --copy flag is set (if you
want to copy content to another server) the data in this column define the
source modules for the copy.

Example usage:

    ./content-copy.py -s prod-dev-user2.json -i Psychology.csv -a 0 1 2 3 -wcr

This will copy chapters 0, 1, 2, and 3 from the Psychology book according to
the csv (or tsv) file, creating workgroups for each chapter, and edit the roles
according to the settings described by settings.json

If the input file is not a bookmap (.csv or .tsv), it should be a copy map
(.out). The format of this file should be:

[destination workspace url] [destination module ID] [source module ID]

The title of the copy map (.out) is not important to the tool.

The script will generate the content-copy map file if the copy
flag is not set. The file will be used to copy the content later with this
tool. Just load it in as the input file instead of a csv.

    -w, --workspaces
        This flag is only useful if the input file is a .csv or.tsv.
        It requires that the input file have chapter titles.

    -c, --copy
        This flag will work if the input file is a .csv, .tsv, or .out.
        It requires that the input file have source module IDs
        (to copy from).

    -r, --roles
        This flag only works in conjuction with the -c, --copy flag.

    -p, --publish
        This flag will only work with .csv and .tsv input files if
        the -c, --copy flag is set. Alternatively, if the input file
        is a .out, this flag can run by itself.

    -a, --chapters
        This flag is used to specify which chapters to operate over in the
        input file. This requires that the input file be a .csv or .tsv.
        The use of this flag is: -a 0 1 2 3 5 6 8 9 or --chapters 4 5 6 1 2 9 10

####Configuring the tool
Before you run the tool, you need to configure the tool. To configure the tool, you will create settings files. 
These files will act like presets of settings for common configurations. These settings files will be json files, 
so be sure to name them [filename].json.

Let’s look at the anatomy of the settings file. The highlighted text is text that you may wish to edit to configure the 
tool. Of course you can edit other portions, but the highlighted parts represent best practices for keeping the rest of 
the process consistent.

1	{
2	   "destination_server": "legacydev.cnx.org", 
3	   "source_server": "legacy.cnx.org",
4	   "credentials": "user2:user2",
5	
6	   "authors": ["user2"],
7	   "maintainers": ["user2", "user1"],
8	   "rightsholders": ["user2", "user3"],
9	
10	   "user1": "user1",
11	   "user3": "user3",
12	
13	   "path_to_tool": "/Users/openstax/cnx/content-copy-tool",
14	   "logfile": "content-copy.log",
15	   "chapter_title_column": "Chapter Title",
16	   "chapter_number_column": "Chapter Number",
17	   "module_title_column": "Module Title",
18	   "source_module_ID_column": "Production Module ID",
19	   "source_workgroup_column": "Production Workgroup",
20	   "destination_module_ID_column": "Dev Module ID",
21	   "destination_workgroup_column": "Dev Workgroup",
22     "unit_number_column": "Unit Number",
23     "unit_title_column": "Unit Title",
24	   "strip_section_numbers": "true"
25	}

Lines 2 and 3 are the urls for the source and destination servers.
Line 4 is the username:password of the user that will be used to create/upload/publish the content.
Lines 6 - 8 are the users that will be entered as the corresponding roles, in this example, for all content processed with this settings file (assuming the alter roles feature is enabled) the creator will be set to user2, the maintainers will be set to user2 and user1, and the rightsholders will be set to user2 and user3. Remember, the value in these lines is a list of usernames, even if only one user is the creator/maintainer/rightsholder the value is a list (with only one username in it), see line 6 as an example.
Lines 10 and 11 are the usernames and passwords for the users that are used in the role altering that are NOT the user in line 4. Note the slight difference in formatting, here the username is the key and the password is the value.
Line 13 is the absolute path to the tool. To find this, open a terminal within the tool’s top directory, (you should see content-copy.py, setup.py, and the lib/ subdirectory), run the command 
pwd 
The output of this command is the working directory (the path to the tool) and will be the value for this line. You should only have to edit this line once. 
Line 14 is the name of the log file for the tool, you should not need to change this, but it might be valuable for reference later.
Line 15 - 23 are the titles of the columns in the input file. The values for these lines must match the column titles in the input file (csv/tsv). However, if the input file does not have one of the optional columns (lines 18 - 23), the names can be whatever you wish them to be. It may be valuable to give them descriptive names that indicate the server they are on, for example. Keep in mind that the input file is a delimiter-separated-values files, so do not use a comma if the file is a .csv or a tab if the file is a .tsv.
Line 25 tells the tool if you would like to remove section numbers from the titles of modules. For example, if the input file has a module titled “1.2 What is Psychology?” then you may want to strip the section numbers. If you choose to do so, the section number will be treated as a separate attribute of the module, in this example the title will become “What is Psychology?”. If you choose not to, the section numbers will be treated as part of the module name. If you want to remove section numbers from the title, set the value to true. If you do NOT want to remove section numbers, set the value to false.



####Install requirements
- python 2.7.6+
- requests
- requests[security]
