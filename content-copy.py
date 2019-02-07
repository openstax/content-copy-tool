#!/usr/bin/env python

# Passthrough for backwards compatibility
print "This command for the CCT is deprecated. Please try the `content-copy` command instead."
import contentcopytool.content_copy as cct
cct.main()