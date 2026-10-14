#!/bin/bash

sudo apt-get update -y
sudo apt-get install vim python-virtualenv python3-dev python3-setuptools -y

#sudo easy_install3 "pip==7.1.2"
cd /vagrant/vagrant_conf
tar xvfz pip-7.1.2.tar.gz
cd pip-7.1.2
sudo python3.2 setup.py install
cd ..
sudo rm -fr pip-7.1.2
cd /

cp /vagrant/example.db /vagrant/pythontutor.db

# Create sandbox for evaldontevil interpreter.
sudo adduser pythontutor-sandbox --gecos "" --disabled-password
sudo mkdir /srv
sudo virtualenv -p python3 /srv/evaldontevil-python

. /vagrant/vagrant_conf/run.sh
