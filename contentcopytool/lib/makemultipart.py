#!/usr/bin/python
import os
import argparse
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders

def makemultipart(atomfile, package, outfile):
    atompart = MIMEBase('application', 'atom+xml')
    atompart.add_header('Content-Disposition', 'attachment; name=atom')
    atompart.set_payload(atomfile.read())

    payloadpart = MIMEBase('application', 'zip')
    payloadpart.add_header('Content-Disposition',
        'attachment; name=payload; filename=%s' % os.path.basename(
            package.name))
    payloadpart.set_payload(package.read())
    Encoders.encode_base64(payloadpart)

    message = MIMEMultipart('related')
    message.attach(atompart)
    message.attach(payloadpart)

    # print(message.as_string(unixfrom=False))
    outfile.write(message.as_string(unixfrom=False))
    outfile.close()


def main():
    parser = argparse.ArgumentParser(description='Create a multipart file from an atom entry and a package '
                                                 '(zip, word, odt)')
    parser.add_argument('atomfile', help='/path/to/atomfile', type=open)
    parser.add_argument('package', help='/path/to/package', type=open)
    parser.add_argument('outfile', help='name of output file', type=argparse.FileType('w + '))
    args = parser.parse_args()
    makemultipart(args.atomfile, args.package, args.outfile)

if __name__ == '__main__':
    main()
