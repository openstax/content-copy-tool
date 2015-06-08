#Content Copy Tool

####Current Status
The content-copy-tool is currently in development. As of 6-8-15, the tool can create placeholder content, copy content, edit roles (in a very static way), and publish modules (post-copy publishing is buggy).

####TODO
- ?better error handling in selenium scripts: always teardown.
- ?quick succession mode for selenium?
- different credentials for source and destination - what will be source and destination
- name uniqueness: workspaces & modules
- config-ify license and url's and stuff
- use sword to create modules

####Install requirements
- python 2.7.6+
- selenium (for selenium portion)
- requests
- requests[security]
