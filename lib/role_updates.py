from os import close, remove
from shutil import move
from tempfile import mkstemp
import re as regex
import traceback
from util import CCTError, SkipSignal, TerminateError
import http_util as http

"""
This file contains the Role Updating related object.
"""

class RoleConfiguration:
    """ Holds  """
    def __init__(self, creators, maintainers, rightholders, settings, credentials):
        self.creators = creators
        self.maintainers = maintainers
        self.rightholders = rightholders
        self.settings = settings
        self.credentials = credentials

class RoleUpdater:
    def __init__(self, role_configuration):
        self.config = role_configuration
    
    def run_update_roles(self, xmlfile):
        self.update_roles(xmlfile, self.prepare_role_updates())

    def update_roles(self, file_path, replace_map):
        """
        Reads through the input file and replaces content according to the replace map

        The replace_map is a list of tuples: (pattern, substitute text)
        """
        fh, abs_path = mkstemp()
        with open(abs_path, 'w') as new_file:
            with open(file_path) as old_file:
                for line in old_file:
                    for pattern, subst in replace_map:
                        line = regex.sub(pattern, subst, line)
                    new_file.write(line)
        close(fh)
        remove(file_path)  # Remove original file
        move(abs_path, file_path)  # Move new file

    def prepare_role_updates(self):
        """
        Updates the roles on a module. This reads in from the settings file for
        creator, maintainer, and rightholder configuration.
        """

        if len(self.config.creators) == 1:
            creator_string = '<dcterms:creator oerdc:id="' + self.config.creators[0] + '"'
        else:
            creator_string = '<dcterms:creator oerdc:id="'
            for creator in self.config.creators[:-1]:
                creator_string += creator + '" oerdc:email="useremail2@localhost.net"' \
                                            ' oerdc:pending="False">' \
                                            'firstname2 lastname2</dcterms:creator>\n' \
                                            '<dcterms:creator oerdc:id="'
            creator_string += self.config.creators[-1] + '"'
        creator_tuple = ('<dcterms:creator oerdc:id=".*"', creator_string)

        if len(self.config.maintainers) == 1:
            maintainer_string = '<oerdc:maintainer oerdc:id="' + self.config.maintainers[0] + '"'
        else:
            maintainer_string = '<oerdc:maintainer oerdc:id="'
            for maintainer in self.config.maintainers[:-1]:
                maintainer_string += maintainer + '" oerdc:email="useremail2@localhost.net" ' \
                                                  'oerdc:pending="False">' \
                                                  'firstname2 lastname2</oerdc:maintainer>\n' \
                                                  '<oerdc:maintainer oerdc:id="'
            maintainer_string += self.config.maintainers[-1] + '"'
        maintainer_tuple = ('<oerdc:maintainer oerdc:id=".*"', maintainer_string)

        if len(self.config.rightholders) == 1:
            rightholder_string = '<dcterms:rightsHolder oerdc:id="' + self.config.rightholders[0] + '"'
        else:
            rightholder_string = '<dcterms:rightsHolder oerdc:id="'
            for rightholder in self.config.rightholders[:-1]:
                rightholder_string += rightholder + '" oerdc:email="useremail2@localhost.net" ' \
                                                    'oerdc:pending="False">' \
                                                    'firstname2 lastname2</dcterms:rightsHolder>\n' \
                                                    '<dcterms:rightsHolder oerdc:id="'
            rightholder_string += self.config.rightholders[-1] + '"'
        rightholder_tuple = ('<dcterms:rightsHolder oerdc:id=".*"', rightholder_string)

        replace_map = [creator_tuple, maintainer_tuple, rightholder_tuple]
        return replace_map

    def get_pending_roles_request_ids(self, copy_config, credentials, logger):
        ids = []
        auth = tuple(credentials.split(':'))
        response1 = http.http_get_request("%s/collaborations" % copy_config.destination_server, auth=auth)
        if not http.verify(response1, logger):
            raise CCTError("FAILURE getting pending role requests: %s %s" % (response1.status_code, response1.reason))
        else:
            html = response1.text
            pattern = regex.compile('name="ids:list" value=".*"')
            matching_items = regex.finditer(pattern, html)
            for match in matching_items:
                string = match.group(0)
                ids.append(string[string.find('value="') + 7:-1])
        return ids

    def get_users_of_roles(self):
        users = set()
        for creator in self.config.creators:
            users.add(creator)
        for maintainer in self.config.maintainers:
            users.add(maintainer)
        for rightholder in self.config.rightholders:
            users.add(rightholder)

        users_and_creds = []
        for user in users:
            try:
                password = self.config.settings[user]
                users_and_creds.append("%s:%s" % (user, password))
            except KeyError:
                if not (self.config.credentials.split(':')[0] == user):
                    raise CCTError("Could not find credentials for user involved in roles, check settings file for: "
                                   + user)
        return users_and_creds

    def accept_roles(self, copy_config, logger, failures):
        try:
            users = self.get_users_of_roles()
        except TerminateError:
            raise TerminateError("Terminate Signaled")
        except (CCTError, Exception) as e:
            if type(e) is not CCTError and type(e) is not SkipSignal:
                logger.error("Problematic Error")
                logger.debug(traceback.format_exc())
            if type(e) is SkipSignal:
                logger.warn("User skipped creating workgroup.")
            logger.error(e.msg)
            logger.error("Not accepting roles")
            return
        for user in users:
            logger.info("Accepting roles for %s" % user)
            parameters = "?"
            for id in self.get_pending_roles_request_ids(copy_config, user, logger):
                parameters += "ids%3Alist=" + id + "&"
            parameters += 'agree=&accept= + Accept + '  # rest of form
            auth = tuple(user.split(':'))
            response = http.http_get_request("%s/updateCollaborations%s" % (copy_config.destination_server, parameters),
                                             auth=auth)  # yes, it is a GET request
            if not http.verify(response, logger):
                logger.error("Failure accepting pending requests for %s %s %s" %
                             (auth[0], response.status_code, response.reason))
                failures.append((auth[0], " accepting pending role requests"))
