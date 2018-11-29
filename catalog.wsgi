#!/usr/bin/python
import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/FlaskApps/")
from Catalog import app as application


application.secret_key = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
