#!/bin/bash

set -x

export SECRET_KEY='8x*1t3+ifh2sv(u-q+p(c8n=ew%igufnc6bet(2tyg@ww(fw*='

cd /vagrant/

sudo pkill -f "manage.py"

sudo pip3 install -v --log venv/install.log -r requirements.txt

cat vagrant_conf/db_admin_credentials.txt | python3 manage.py syncdb
python3 manage.py migrate tutorial
python3 manage.py collectstatic --noinput

python3 manage.py runserver 0.0.0.0:8042
