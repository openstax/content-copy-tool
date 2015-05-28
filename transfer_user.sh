#!/bin/bash

usage()
{
cat << EOF
usage: $0 options mapping_file.txt

This script transfers published modules from one machine to unpublished copies on another

OPTIONS:
   -h      Show this message
   -f      Source machine (from)
   -s      Source username:password (optional)
   -u      Destination username:password
   -v      Verbose
   -n      Noact -- dryrun

mapping_file.txt is a whitespace separated 3 column text file, containing:
To URL (usually a workgroup), To moduleid, From moduleid

The To moduleid must already be checked  in the workgroup specified (TODO: check it out)
The From moduleid will be exported from the published version on the From machine (TODO: allow use of checkout modules)
EOF
}

TEST=
SERVER=
PASSWD=
VERBOSE=
NOACT=
while getopts “hf:s:u:vn” OPTION
do
     case $OPTION in
         h)
             usage
             exit 1
             ;;
         f)
             FROM=$OPTARG
             ;;
         s)
             FROMUSER=$OPTARG
             ;;
         u)
             TOUSER=$OPTARG
             ;;
         v)
             VERBOSE=1
             ;;
         n)
             NOACT=1
             ;;
         ?)
             usage
             exit
             ;;
     esac
done
shift $((OPTIND-1))

if [[ -z $FROM ]] || [[ -z $TOUSER ]]
then
     usage
     exit 1
fi

# need to test for a mapping file here

tmpdir=$(mktemp -d -t fooobar)

username=${TOUSER%:*}

while read tURL tMOD fMOD
do
echo $tURL $tMOD $fMOD
echo "move http://${FROM}/content/${fMOD}/latest to ${tURL}/${tMOD}"
# echo $tmpdir

if [[ -z $NOACT ]]
then
    # grab zip
    curl -q http://$FROM/content/$fMOD/latest/module_export?format=zip > $tmpdir/$fMOD.zip

    # grab xml metadata
    curl -q http://$FROM/content/$fMOD/latest/rhaptos-deposit-receipt > $tmpdir/$fMOD.xml

    # change ids in the metadata
    sed -e "s/<dcterms:creator oerdc:id=.*/<dcterms:creator oerdc:id=\"$username\"/" -i bak $tmpdir/$fMOD.xml
    sed -e "s/<dcterms:rightsHolder oerdc:id=.*/<dcterms:rightsHolder oerdc:id=\"$username\"/" -i bak $tmpdir/$fMOD.xml
    sed -e "s/<oerdc:maintainer oerdc:id=.*/<oerdc:maintainer \
    oerdc:id=\"$username\" \
    oerdc:pending=\"False\">OpenStax College<\/oerdc:maintainer><oerdc:maintainer \
    oerdc:id=\"$username\"/" -i bak $tmpdir/$fMOD.xml

    # make multi
    python makemultipart.py $tmpdir/$fMOD.xml $tmpdir/$fMOD.zip $tmpdir/$fMOD.mpart
    # upload multi via API
    BOUNDARY=$(grep -m 1 boundary  $tmpdir/$fMOD.mpart | sed -e 's/^.*"\([^"]*\)".*$/\1/')
    curl -v --request POST --user $TOUSER \
      --header "Content-Type: multipart/related;boundary=$BOUNDARY;type=application/atom+xml" \
      --header "In-Progress: true" \
      --upload-file $tmpdir/$fMOD.mpart $tURL/$tMOD/sword

fi
done <$1

exit
