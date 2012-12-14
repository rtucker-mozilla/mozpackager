mozpackager
=======

Installation Instructions
=========================

{{{
git@github.com:rtucker-mozilla/mozpackager.git  
cd mozpackager
virtualenv --distribute .virtualenv  
source .virtualenv/bin/activate  
git submodule init 
git submodule update --recursive  
pip install -r requirements/new.txt  
sudo yum install rabbitmq-server
}}}



More readme coming soon  
