## Content Copy Tool - User Manual
#### Description
The Content Copy Tool is a development tool to copy content from one cnx server
to another. The tool is a python script that runs via the command line.


#### What’s in the box
The tool is made up of a set of scripts:
```
content-copy.py
setup.sh
example-settings.json
example-input.tsv
__init__.py
lib/
    bookmap.py
    command_line_interface.py
    http_util.py
    makemultipart.py
    operation_objects.py
    role_updates.py
    util.py
    __init__.py
```

content-copy.py is the primary script, but before you run the tool, you need to
set it up.

#### Setting up the tool
* If you are using git (recommended), from the Documents folder enter the command 
```git clone https://github.com/Rhaptos/content-copy-tool.git```
This will copy the tool down to your machine and put the contents into the content-copy-tool folder.
* If you are using git (recommended), to get the latest version of the tool, navigate to the tool’s 
top directory (see beginning of step 5), and enter the command `git pull`. This will update your tool 
with the latest version. You can skip to step 5.
* If you are NOT using git, Create a new folder in your Documents folder called content-copy-tool
* If you are NOT using git, Extract the content-copy-tool zip contents into this folder. The rest of 
these instructions assume that the top directory of the tool is in Documents/content-copy-tool. To 
confirm, this, you should see `content-copy.py`, `setup.sh`, `example-settings.json`, `example-input.tsv`, 
and `lib/` in `Documents/content-copy-tool`.
* Open a terminal in the tool’s top directory: open Terminal, enter the command
```
cd ~/Documents/content-copy-tool
```
(see Enabling “Open Terminal At Folder” Service section for how to do this
through Finder). Note: this command will
bring you to the top level directory of the tool from anywhere in a terminal.

* Run the following command to set up the tool. This script will install all the
necessary packages for using the tool.
```
sh setup.sh
```
* The first thing you should do is create a settings file. Start by opening the
`example_settings.json` file in a text editor.
* If you have placed the tool in the directory `Documents/content-copy-tool`
change the path_to_tool value to be
`/Users/yourusername/Documents/content-copy-tool`.
* If you have placed it elsewhere, be sure to enter the proper path, see
Configuring the tool section, about line 13 for details.
* Modify the settings file to configure the tool, see Configuring the tool
section.
* Save this modified settings file as `mysettings.json` or something similar.
Now when you need to create a new settings configuration, open this file, make
your edits, and save it as a new file with a descriptive name, like
`staging3-to-prod-OSCPsych.json`. Meaning: settings for copying content from
staging3 server to production server with user OSCPsych. You will have to edit
the data within the file to make it actually do this though.
* The tool should now be set up! Make a settings file for your work and get
content copying!

#### Configuring the tool
Before you run the tool, you need to configure the tool. To configure the tool,
you will create settings files. These files will act like presets of settings
for common configurations. These settings files will be json files, so be sure
to name them `[filename].json`. If you are unfamiliar with json files, please
read through the Understanding Json section at the bottom.

Let’s look at the anatomy of the settings file. The highlighted text is text
that you may wish to edit to configure the tool. Of course you can edit other
portions, but the highlighted parts represent best practices for keeping the
rest of the process consistent.
```
1	{
2	   "destination_server": "https://legacydev.cnx.org",
3	   "source_server": "https://legacy.cnx.org",
4	   "destination_credentials": "user2:user2password",
5
6	   "authors": ["user2"],
7	   "maintainers": ["user2", "user1"],
8	   "rightsholders": ["user3"],
9
10	   "user1": "user1password",
11	   "user3": "user3password",
12
13	   "path_to_tool": "/Users/openstax/cnx/content-copy-tool",
14	   "logfile": "content-copy.log",
15	   "chapter_title_column": "Chapter Title",
16	   "chapter_number_column": "Chapter Number",
17	   "module_title_column": "Module Title",
18	   "source_module_ID_column": "Production Module ID",
19	   "destination_module_ID_column": "Dev Module ID",
20	   "destination_workgroup_column": "Dev Workgroup",
21	   "unit_number_column": "Unit Number",
22	   "unit_title_column": "Unit Title",
23	   "strip_section_numbers": "true"
24	}
```
* Lines 2 and 3 are the urls for the source and destination servers.
* Line 4 is the username:password of the user that will be used to
create/upload/publish the content on the destination server.
* Lines 6 - 8 are the users that will be entered as the corresponding roles, in
this example, for all content processed
with this settings file (assuming the alter roles feature is enabled) the author
will be set to user2, the maintainers
will be set to user2 and user1, and the rightsholders will be set to user2 and
user3. Remember, the value in these lines is a list of usernames, even if only
one user is the author/maintainer/rightsholder the value is a list (with only
one username in it), see line 6 as an example.
* Lines 10 and 11 are the usernames and passwords for the users that are used in
the role altering that are NOT the user in line 4. Note the slight difference in
formatting, here the username is the key and the password is the value.
* Line 13 is the absolute path to the tool. To find this, open a terminal within
the tool’s top directory, (you should
see `content-copy.py`, `setup.py`, and the `lib/` subdirectory), run the command
`pwd` The output of this command is the working directory (the path to the tool)
and will be the value for this line. You should only have to edit this line once
(unless you move the tool to a different directory).
* Line 14 is the name of the log file for the tool, you should not need to
change this, but it might be valuable for reference later.
* Line 15 - 22 are the titles of the columns in the input file. The values for
these lines must match the column titles in the input file (csv/tsv). However,
if the input file does not have one of the optional columns (lines 18 - 22), the
names can be whatever you wish them to be. It may be valuable to give them
descriptive names that indicate the server they are on, for example. Keep in
mind that the input file is a delimiter-separated-values files, so do not use a
comma if the file is a .csv or a tab if the file is a .tsv.
* Line 23 tells the tool if you would like to remove section numbers from the
titles of modules. For example, if the input file has a module titled “1.2 What
is Psychology?” then you may want to strip the section numbers. If you choose to
do so, the section number will be treated as a separate attribute of the module,
in this example the title will become “What is Psychology?”. If you choose not
to, the section numbers will be treated as part of the module name. If you want
to remove section numbers from the title, set the value to true. If you do NOT
want to remove section numbers, set the value to false.

#### Running the tool
Before you run the tool, be sure that you are in the tool’s top directory. To
run the tool enter the command:
```
./content-copy.py --settings [settings file] --input-file [input file] [options]
```
Where [settings file] is the name of the settings file, [input file] is the name
of the input file, and [options] are the run options. If you are unfamiliar with
running programs from the command line, consider reading the Understanding the
Command Line Interfaces section at the bottom.

If you need an explanation of the tool from within the terminal, run
```
./content-copy.py --help or ./content-copy.py -h
```
This will display the usage and explanation of the content copy tool.

##### Options
The tool runs based on the provided command line arguments. Required arguments
are:
```
-s, --settings [settings file]
    The settings file to configure the tool with source, destination servers,
    and other settings. for more information, see Configuring the tool section.
-i, --input-file [input file]
    The input file that contains the data to operate on. This should be the
    csv/tsv file that corresponds to the bookmap spreadsheet. It has required
    columns:
    [Chapter Number],[Chapter Title],[Module Title]. The minimum data required
    is the module titles and chapter number, see Input File Explained section.
```

Once you have these arguments, the tool now knows what configuration to use and
what data to operate on, now you must tell it what to do with the data. Here are
your options:
```
-m, --modules
    Create placeholder modules for the content on the destination server.
-w, --workgroups
    Create placeholder workgroups for each chapter of content on the destination
    server. Note, if this option is used, the -m, --modules is redundant. The
    workgroups are titled [Title of input file] - [Chapter Title]
-u, --units
    Create sub-collections for units and place chapter collections in the unit
    collections. The input file must have unit_number_column and
    unit_title_column entries.
-c, --copy
    Copy content from source server to destination server. Note: if this option
    is used, the input file must have a source_module_id column with data for
    each module.
-r, --roles
    Update the roles according to the configuration file for each module. Note,
    this option must be used in conjunction with the -c, --copy option.
-o, --collection
    Create a collection for the book, create sub-collections for each chapter,
    and populate the collection with the content.
-p, --publish
    Publish modules on the destination server. Note, if this option is used, the
    input file must have destination_module_id column with data for each module.
--publish-collection
    Publish the collection after creating it. Note: this must be used in
    conjunction with -o, --collection flag.
--accept-roles
    Accept the pending role requests for the users in the
    author/maintainer/rightsholder lines in the setting file. Note, to use this
    option, the settings file must have “username”: “password” entries for each
    user in the author/maintainer/rightsholder lines. NOTE: this option will
    automatically accept every pending role request for the users in the
    author/maintainer/rightsholder lines.
--dry-run
    Parses the input file data and steps through the other options without
    creating/copying/altering/publishing any content.
```
Until now, the tool has been operating on every entry in the input file. But
sometimes the input file has an entire book’s worth of data and you only want to
use the tool on one (or just a few) chapters. One option is to remove the data
from the input file (or the spreadsheet) but this is destructive and messy.
Instead, you can use an additional option with the content copy tool.
```
-a, --chapters [chapters]
```
The tool will only operate on the chapters that correspond to the input file’s
chapter_number column. For example, if you only want to operate on chapter 1,
use the option `--chapters 1` or `-a 1` and the tool will only operate on the
entries that have a 1 in the chapter_number column.

Alternatively, you can specify which chapters you do NOT want to operate on
with:
```
--exclude-chapters [chapters to exclude]
```
Note, this will override the `-a, --chapters` option. So, if you use both `-a 1`
`--exclude-chapters 1`, the tool will operate on zero chapters.

##### What you will see
When the tool begins, it will display a summary of what it is about to do, and
ask for confirmation. enter 1 to proceed and 2 to cancel.

When the tool completes, if it created placeholders, it will create an output
file (with the added data) and display thefilename. This file will be in the top
directory of the tool.

##### Example Uses
Here are some example use cases (these assume the settings files have been
created correctly):

You want to create placeholder modules and workgroups on production for chapters
1, 2, and 3 of Psychology.
```
./content-copy.py -s staging3-prod-OSCPsych.json -i Psychology.tsv -a 1 2 3 -w
```

You want to copy the modules from staging3 to production for chapters 1, 2, and
3 of Psychology and alter the roles.
```
./content-copy.py -s staging3-prod-OSCPsych.json -i Psychology.tsv -a 1 2 3 -cr
```

You want to create placeholder modules and workgroups on production for chapters
8, 9, 10, 11, and 12 of Psychology, copy the copy the content from staging3 to
production for those chapters of Psychology, and alter the roles.
```
./content-copy.py -s staging3-prod-OSCPsych.json -i Psychology.tsv -a 8 9 10 11 -wcr
```

You want to create only placeholder modules on production for the remaining
chapters in Psychology, copy the content over but not update the roles.
```
./content-copy.py -s staging3-prod-OSCPsych.json -i Psychology.tsv --exclude-chapters 1 2 3 8 9 10 11 -mc
```

You want to accept all of the pending role requests and publish all of
Psychology.
```
./content-copy.py -s staging3-prod-OSCPsych.json -i Psychology.tsv --accept-roles -p
```

You want to create placeholder modules on naginata for four specific modules,
copy the content over and publish them.
```
./content-copy.py -s prod-naginata-qaUser.json -i check.tsv -mcp
```
Here the input file is special, since this is just a few specific modules, the
bookmap full of entries will be overload. The input file may look something like
this:
```
Module Title,Production Module ID,Chapter Number
BrokenModule1,m12345,0
BrokenModule2,m23456,0
BrokenModule3,m34567,0
BrokenModule4,m45678,0
```

##### Skipping and Terminating
If the tool gets stuck on a task, you can tell it to skip the task it is working on.
To skip the current tasks, press `Ctrl+z`. This will tell the tool to skip the module
(or workgroup or collection) that it is processing and treat it as failed. This process
is somewhat dangerous and should not be used lightly. It is most helpful when you see 
the notification of a potential stall in the process.

If you decide that you want to prematurely stop the tool in its tracks, you can terminate
the process by pressing `Ctrl+c`. This will terminate the process, but the bookmap's
state will be saved in `[INPUT FILE NAME]_error_[TIMESTAMP].tsv` (or csv).

#### Input File Explained
The input file contains the data that the tool will operate on. It is a list of
modules. The title of the file should be the title of the book (this is most
important for the workgroup creation). The format of the file can be either csv
(comma separated values) or tsv (tab separated values) files. The required
columns are chapter_number and module_title, every input file must have these
columns and data in them for each entry. Running the basic -m, --modules option
will create the destination_module_id column and the destination_workgroup
column (and appropriate data). Here are the requirements for specific uses.

If the user wants to create workgroups for the modules (by chapter), the file
needs a chapter_title column with data for each module.

If the user wants to copy data, the file needs a source_module_id column with
data in it for each module to be copied.

If the user wants to publish data, the file needs the destination_module_id
column and the destination_workgroup column with data for each module.

#### Understanding the Command Line Interface
Command line programs run in a terminal and do not have graphical windows. So
instead of a Graphical User Interface, the programs use a Command Line
Interface. When running a command line program, you enter the name of the
program you want  to run. In this case, the program is called content-copy. If
the file you are running (in this case, content-copy.py) is an executable file,
you can run the program with the “./” indicator at the beginning, for example,
```
./content-copy.py  
```
When you run a command line program, you can pass it arguments, or parameters,
that modify or specify what the program will do. Often times, these arguments
are accompanied by indicators called flags that denote which argument/parameter
the input corresponds to. The flags are simply a dash, then a single letter, for
example, `-h`. This is a common flag for command line programs that prints a
help message. Command line flags can also come in long form, for example,
`--help` which means the exact same thing as `-h`, it’s just easier to read (and
longer to type).

Sometimes, flags take in a value. This is often done by entering a space after
the flag, and then the input value, for example, `-s example_settings.json`.
This sets the `-s` flag’s value to be example_settings.json. Using the long form
flags works the same way, `--settings example_settings.json`. Further, some
flags will accept multiple values, for example, `--chapters 1 2 3 4` will set
the chapters flag to a list of [1, 2, 3, 4].

For more information on command line interfaces, check out wikipedia, or ask a
developer.
https://en.wikipedia.org/wiki/Command-line_interface

Understanding Json
Json is a file format that is easy for both humans and computers to read. A
basic explanation of json follows.

A json file is made up of a collection of key/value pairs. For example,
“credentials”: “user2:user2”. In this case, the key is “credentials” and the
value is “user2:user2”. Notice that the key and value are separated by a colon.
Pairs are separated by a comma. Json files group collections with the { and }
characters.

Json keys and values can be:
* strings -some text within quotation marks “ “
* a collection -pairs within curly braces { } or,
* a list of values -strings, collections, or lists within square brackets [ ].

When being parsed by a computer, the computer uses the keys to lookup the
values, in just the way that you use a word as a key to look up a definition in
a dictionary. There is much more to json, if you are interested check out
http://json.org/.  

#### Enabling “Open Terminal At Folder” on Mac OS
When you open the Terminal application, it opens to your home directory. This is
like opening Finder and opening the yourusername folder. To use the
content-copy-tool, you need to to navigate to the tool’s top directory from
within the terminal. This is often done with the cd command (short for “change
directory”). However, Mac OS provides a service to open a Terminal window from
Finder that opens to a specific directory.

To enable the service, go to System Preferences > Keyboard > Shortcuts >
Services, under Files and Folders, check the box for New Terminal at Folder (you
can use New Terminal Tab at Folder, the option is up to you).

To use the service, use Finder to navigate to the folder you want to open your
terminal in, in our case, select content-copy-tool. Secondary click on the
folder, select Services > New Terminal at Folder. It might take a moment to
open, but should pull up a terminal at that location.

#### Pro-Tip
For long runs that might take a while, it is important to keep you machine awake 
while the process is running. If it goes to sleep, the tool will hang up and won’t 
be able to complete successfully. To keep your mac from going to sleep (if you are 
stepping away from your computer), you can use the `caffeinate` tool to keep it awake. 
To use this you will prepend `caffeinate -i` to the front of the tool’s command, for example:
```
caffeinate -i ./content-copy.py -s settings.json -i input.tsv -wcop
```
