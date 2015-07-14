#!/bin/bash

easy_install --user requests
easy_install --user requests[security]

chmod +x content-copy.py