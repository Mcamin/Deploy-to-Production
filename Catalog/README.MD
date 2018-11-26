# Udacity Catalog Project

### Requirements:

##### 1. install  Install <a target="_blank" href="https://www.vagrantup.com/">Vagrant</a> and <a target="_blank" href="https://www.virtualbox.org/">VirtualBox</a>

##### 2. Clone <a target="_blank" href="https://github.com/udacity/fullstack-nanodegree-vm">the fullstack-nanodegree-vm</a>. This contain all the needed configuration.


##### 3. Launch the Vagrant VM

    vagrant up

##### 4. connect to Vagrant VM

    vagrant ssh

##### 5. clone this project inside the vagrant folder and open the project directory
    cd /Catalog-Project-master

##### 6. launch the Webserver.py
      python webserver.py

##### 7. In case the database was deleted, a new one can be created using the following command:
      python config.py

* ###### Open <a target="_blank" href="http://localhost:5000/">Localhost</a>.

<br/>
    **** User Table *****

| Column | Type                     |
|--------|--------------------------|
| id | integer - PK              |
| name  | string                     |
| email   | string                     |
| picture   | string                     |

<br/>
**** Category Table *****

| Column | Type    |
|--------|---------|
| name   | string    |
| user_id    | integer - FK    |
| id     | integer - PK |

<br/>
**** Product Table *****

| Column | Type    |
|--------|---------|
| id   | integer - PK |
| name    | string    |
| description | string |
| brand | string |
| price     | string |
| user_id     | integer - FK |
| category_id     | integer - FK |
