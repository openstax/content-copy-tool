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


####Install requirements
- python 2.7.6+
- selenium (for selenium portion)
- requests
- requests[security]
