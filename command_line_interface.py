import argparse
from argparse import RawDescriptionHelpFormatter
import sys

description="""The Content-Copy-Tool is configurable. The first way of configuring it
is through the settings file (see usage below). The settings file must be saved
as a '*.json' file. This file contains settings such as source and destination
servers, user credentials, and some other potentially dynamic information.

The second way to configure the tool is with the type of file provided as the
input file. If the input file is a '*.csv' or '*.tsv' file, the tool will
proceed to create placeholder modules on the destination server (other options
can modify this behavior some). If the input file is a '*.out' file, the tool
will  not create placeholders, if the proper options are set (see below), it
will copy and/or publish the modules described in the input file.

The third way to configure the tool is through the control options. With these
options you can tell the tool to create workgroups for each chapter of content,
copy content from one server to another, modify roles on each module according
to the settings file, and/or publish the copied content. The other options
allow you to specify which chapters you want the tool to operate on and execute
a dry-run of the procedure. See below for examples.
"""

epi = """The input file should be in the following form (commas can be replaced with tabs):

Chapter Number,Chapter Title,Module Title,Module ID
5,History of Rice University,5.1 The Founding of the Institution,m53341

and the title of the file should be [the title of the book].csv
Alternatively, the tool can accept a .tsv (tab separated values) file.
The Module ID is only required if the -c, --copy flag is set (if you
want to copy content to another server) the data in this column define the
source modules for the copy.

Example usage:
./cct.py -s settings.json -i Psychology.csv -a 0 1 2 3 -wcr

This will copy chapters 0, 1, 2, and 3 from the Psychology book according to
the csv (or tsv) file, creating workgroups for each chapter, and edit the roles
according to the settings described by settings.json

If the input file is not a bookmap (*.csv or *.tsv), it should be a copy map
(*.out). The format of this file should be:
[destination workspace url] [destination module ID] [source module ID]

The title of the copy map (*.out) is not important to the tool.

The script will generate the content-copy map file if the copy
flag is not set. The file will be used to copy the content later with this
tool. Just load it in as the input file instead of a csv.

-w, --workspaces
    This flag is only useful if the input file is a '*.csv' or '*.tsv'. It
    requires that the input file have chapter titles.
-c, --copy
    This flag will work if the input file is a '*.csv', '*.tsv', or '*.out'. It
    requires that the input file have source module IDs (to copy from).
-r, --roles
    This flag only works in conjuction with the -c, --copy flag.
-p, --publish
    This flag will only work with '*.csv' and '*.tsv' input files if the -c,
    --copy flag is set. Alternatively, if the input file is a '*.out', this flag
    can run by itself.
-a, --chapters
    This flag is used to specify which chapters to operate over in the input
    file. This requires that the input file be a '*.csv' or '*.tsv'. The use of
    this flag is: -a 0 1 2 3 5 6 8 9  or  --chapters 4 5 6 1 2 9 10
"""

def get_parser(version):
    parser = argparse.ArgumentParser(description=description, prog="content-copy.py", usage='%(prog)s -s SETTINGS -i INPUT [options]', epilog=epi, formatter_class=RawDescriptionHelpFormatter)

    required_args = parser.add_argument_group("Required Arguments")
    required_args.add_argument("-s", "--settings", action="store", dest="settings", required=True, help="Settings file path")
    required_args.add_argument("-i", "--input-file", action="store", dest="input_file", required=True, help="The input file path")

    control_args = parser.add_argument_group("Control and Options Arguments (Optional)", "These arguments let you define exactly what you want to do on this run.")
    control_args.add_argument("-w", "--workgroups", action="store_true", dest="workgroups", help="Create workgroups for chapter titles (the input data must have chapter titles if enabled).")
    control_args.add_argument("-c", "--copy", action="store_true", dest="copy", help="Use this flag to copy the data from source server to destination server. Without this flag, no content will be copied over. When using this flag, input file must have a source module ID column filled for each module that will be copied.")
    control_args.add_argument("-r", "--roles", action="store_true", dest="roles", help="Use this flag is you want to update the roles according to the settings (.json) file. This flag only works if -c, --copy flag is also set.")
    control_args.add_argument("--accept-roles", action="store_true", dest="accept_roles", help="Use this flag to automatically accept the roles requests.")
    control_args.add_argument("-p", "--publish", action="store_true", dest="publish", help="Use this flag to publish the modules after copying content to the destination server.")
    control_args.add_argument("-a", "--chapters", action="store", dest="chapters", nargs="*", help="Which chapters to copy (optional).")
    control_args.add_argument("--dry-run", action="store_true", dest="dryrun", help="Steps through input processing, but does NOT create or copy any content. This is used for checking input file correctness (optional).")
    control_args.add_argument("-e", "--selenium", action="store_true", dest="selenium", help="Use this flag to use selenium for placeholder creation.")

    parser.add_argument("--version", action="version", version=version, help="Prints the tool's version")

    return parser

def verify_args(args):
    if args.accept_roles:
        print "WARNING: The accept roles function accepts ALL pending role requests for users listed in creators, maintainers, or rightholders."
    if args.roles and not args.copy:
        print "ERROR: using -r, --roles requires the use of -c, --copy."
        sys.exit()
    if args.publish and (args.input_file.endswith(".csv") or args.input_file.endswith(".tsv")) and not args.copy:
        print "ERROR: can only publish content from '*.csv' or '*.tsv' when using -c, --copy."
        sys.exit()
