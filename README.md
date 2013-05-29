# mozpackager

## Requirements

* python
  * virtualenv will probably make your life easier
* rabbitmq server

## Installation Instructions

```
git clone https://github.com/rtucker-mozilla/mozpackager.git
cd mozpackager
virtualenv --distribute .virtualenv  
source .virtualenv/bin/activate  
git submodule init 
git submodule update --recursive  
pip install -r requirements/new.txt  
```

## More readme coming soon  
