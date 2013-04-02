#!/bin/bash

## This needs to be the full absolute path of the file
FILENAME=$1
PACKAGE_SOURCE_DIR=''
DEB_BUILD_DIR='/tmp/deb_build_dir'
WORKING_DIR=$(pwd)

if [[ $FILENAME == *.rpm ]]; then
    FILETYPE='rpm'
fi

if [[ $FILENAME == *.deb ]]; then
    FILETYPE='deb'
fi
if [ -z $FILETYPE ]; then
    echo "Unknown File Type"
    exit 2
fi

pgrep -u mozpackager_sign gpg-agent >/dev/null
if [ $? -ne 0 ]; then
   gpg-agent --daemon --write-env-file /home/mozpackager_sign/.gnupg/agent.info
fi

source /home/mozpackager_sign/.gnupg/agent.info
export GPG_AGENT_INFO

response_status='OK'
message='Packaged Signed Successfully'
case $FILETYPE in 
    'deb' )
        if [ -d $DEB_BUILD_DIR ]; then
            rm -rf $DEB_BUILD_DIR
        fi 
        mkdir $DEB_BUILD_DIR
        if [ -a $FILENAME ]; then
            cp $FILENAME $DEB_BUILD_DIR
            cd $DEB_BUILD_DIR
            ar x $FILENAME
            rm $FILENAME
            cat debian-binary control.tar.gz data.tar.gz > combined_contents
            
            gpg -abs -o _gpgorigin combined_contents
            if [ $? != 0 ]; then
                message='Unable to sign DEB'
                response_status='FAILED'
            fi
            ar rc $FILENAME debian-binary control.tar.gz data.tar.gz _gpgorigin
            mv $FILENAME $WORKING_DIR/../package_builds/
            rm -rf $DEB_BUILD_DIR
        
        fi 
        echo '====={"success": "'$response_status'", "message":"'$message'"}'
        ;; 
    'rpm' )
        /home/mozpackager_sign/rpmsign.exp $FILENAME 2>&1
        if [ $? != 0 ]; then
            message='Unable to sign RPM'
            response_status='FAILED'
        fi 
        echo '====={"success": "'$response_status'", "message":"'$message'"}'
        ;; 
    * )
        message='Unknown File Type'
        response_status='FAILED'
        echo '====={"success": "'$response_status'", "message":"'$message'"}'
        exit 2;;
esac
