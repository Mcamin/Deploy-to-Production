# A Flask app Deployment on Lightsail

A basic Catalog App  with correct folder structure for deployment , also included a wsgi file for deployment to a apache server.

##Motivation
  The Project is for the Udacity Fullstack Nano Degree. its aims to deploy a Flask App on apache2 server. I hope this template and guide makes using and deploying flask apps easier for other developers.
  
## Example

```python

Folder Hiearchy

Catalog
   templates
   static
     css
      .css files
     js
       .js files
   __init__.py
   config.py
catalog.wsgi

```

## Guide

1) Download the zip file and extract to the location of choice

2) Navigate to your Catalog/venv and add a requirements.txt file to include the packages your app requires or just install them manually.

3) Rename the folder called Catalog to your app name.

4) Rename the .wsgi file to your app name, preferably in lowercase to the app name

For example lets say we had a folder called FlaskApp which holds all your flask apps on the server, and your app your are deploying was called FlaskApp, your folder structure on the server should look like this once deployed.

```python

FlaskApps
  Catalog
    static
    templates
    venv
    __init__.py 
    other .py Files
  catalog.wsgi

```  


5)Once your folder is deployed to the server, navigate to Catalog/venv and type the
  command virtualenv.(the period represents the current directory) and will install all python dependencies in the venv folder. 

6)Still in the folder venv type the command source bin/activate which will activate the virtualenv.
  Then install all packages required by your app by running the command pip install -r requirements.txt. or install them manually.

7)Edit the catalog.wsgi file and change the commands as required  

The wsgi file for deploying this app would look like this:

```python

#!/usr/bin/python
import sys
import logging

logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/FlaskApps/")
from Catalog import app as application


application.secret_key = 'Add your secret key'

```

8) Next create a .conf file in your site-available folder by running the following command below.

```python

sudo nano /etc/apache2/sites-available/FlaskApp.conf  where FlaskApp is the name of the app

```

####example content for the FlaskApp.conf file

```python

<VirtualHost *:80>
                ServerName DomainName or Server Ip
                ServerAdmin admin@mywebsite.com
                WSGIScriptAlias / /var/www/FlaskApps/catalog.wsgi
                <Directory /var/www/FlaskApps/Catalog/>
                        Order allow,deny
                        Allow from all
                </Directory>
                Alias /static /var/www/FlaskApps/Catalog/static
                <Directory /var/www/FlaskAppsy/Catalog/static/>
                        Order allow,deny
                        Allow from all
                </Directory>
                ErrorLog ${APACHE_LOG_DIR}/error.log
                LogLevel warn
                CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>



```

9) then run the command sudo a2ensite FlaskApp.conf.

10) Lastly we need to give apache access to the folders. navigate to
    
    /var/www/FlaskApp and type the command

    chown -R www-data:www-data FlaskApp

11) run the command
  
    sudo service apache2 reload

This should be all your need to deploy your app to a apache server.

