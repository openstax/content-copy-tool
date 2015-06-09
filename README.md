#Content Copy Tool

####Current Status
The content-copy-tool is currently in development. As of 6-8-15, the tool can create placeholder content, copy content, edit roles (in a very static way), and publish modules.

####TODO
- ?better error handling in selenium scripts: always teardown.
- ?quick succession mode for selenium?
- different credentials for source and destination - what will be source and destination
- name uniqueness: workspaces & modules
- config-ify license and url's and stuff
- ?use sword to create/publish modules
- infrastructure for user-working directory
- look into pending role requests
- should the roles information be in the confirmation summary?


####Install requirements
- python 2.7.6+
- selenium (for selenium portion)
- requests
- requests[security]
