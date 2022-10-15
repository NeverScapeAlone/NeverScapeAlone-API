# NeverScapeAlone-API Repository

# Setting up your environment

__Requirements__
* Ubuntu 22.04 or a cheap server that can be used to run the following commands:

### INSTALLING Nginx
```
sudo apt update
sudo apt install nginx
sudo ufw allow 'Nginx HTTP'
sudo ufw allow 22 #ssh
sudo ufw allow 80 # http
sudo ufw allow 443 # https
sudo ufw allow 3306 # Mysql
sudo ufw allow 5500 # NeverScapeAlone main branch
sudo ufw allow 5501 # NeverScapeAlone development branch
sudo ufw allow 6379 # Redis
sudo ufw enable
sudo ufw reload
sudo ufw status
```

### INSTALLING Mysql
```
sudo apt install mysql-server
sudo mysql
> ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'password';
> FLUSH PRIVILEGES;
> exit
```

### INSTALLING Php
```
sudo apt install php-fpm php-mysql
sudo nano /etc/nginx/sites-available/site

# INPUT THE FOLLOWING
server {
        listen 80;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name site;

        location / {
                try_files $uri $uri/ =404;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
}

sudo ln -s /etc/nginx/sites-available/site /etc/nginx/sites-enabled/
sudo unlink /etc/nginx/sites-enabled/default
sudo systemctl reload nginx
```

## INSTALLING Docker
```
sudo apt-get update
sudo apt-get install \
                ca-certificates \
                curl \
                gnupg \
                lsb-release

sudo mkdir -p /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo service docker start
sudo docker run hello-world
```

### INSTALLING Docker Compose
```
sudo apt install docker-compose
```

### OPENING MYSQL TO THE WORLD
```
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

>> CHANGE BIND ADDRESS TO THIS:
bind_address = {YOUR IPV4 HERE}

sudo service mysql restart
systemctl status mysql.service
sudo mysql -u root -p

# ENTER YOUR PASSWORD "password" if you didn't change the default
> CREATE USER 'username'@'%' IDENTIFIED BY 'chooseyourpassword';
> GRANT ALL PRIVILEGES ON *.* TO 'username'@'%';
> FLUSH PRIVILEGES;
> exit

sudo systemctl restart nginx
```

### INSTALLING PHPMYADMIN
```
sudo apt install phpmyadmin
sudo nano /etc/nginx/snippets/phpmyadmin.conf

# PLACE THIS IN THE phpmyadmin.conf FILE

location /phpmyadmin {
    root /usr/share/;
    index index.php index.html index.htm;
    location ~ ^/phpmyadmin/(.+\.php)$ {
        try_files $uri =404;
        root /usr/share/;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include /etc/nginx/fastcgi_params;
    }

    location ~* ^/phpmyadmin/(.+\.(jpg|jpeg|gif|css|png|js|ico|html|xml|txt))$ {
        root /usr/share/;
    }
}

sudo nano /etc/nginx/sites-available/site

# REPLACE THE OLD FILE WITH THIS
server {
        listen 80;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name site;
        include snippets/phpmyadmin.conf;

        location / {
                try_files $uri $uri/ =404;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
}

sudo service nginx restart

## you can now go to http://{youripv4domain}.com/phpmyadmin and login to your mysql database
```

# Entering in the NeverScapeAlone-API mysql files:
Use the file located here to generate a series of tables that you will use for your mysql database:
https://github.com/NeverScapeAlone/NeverScapeAlone-SQL/blob/main/full_setup.sql

### INSTALLING REDIS
```
sudo apt update
sudo apt install redis-server
sudo nano /etc/redis/redis.conf
# IN THE redis.conf file, change the following lines:
> supervised no -> supervised systemd
> bind 127.0.0.1 ::-1 -> bind 0.0.0.0
> #requirepass -> requirepass <put a strong password here>

sudo systemctl restart redis.service
sudo systemctl status redis
redis-cli
> Auth <your very strong password from requirepass>
> ping
>> PONG
> exit
```

### GITHUB RUNNER
1. On your fork of the repository go to:
2. Settings > Actions > Runners > new self-hosted runner
3. Follow the commands listed
4. Set up your runner as a service here: https://docs.github.com/en/actions/hosting-your-own-runners/configuring-the-self-hosted-runner-application-as-a-service
```
sudo ./svc.sh install
sudo ./svc.sh start
```

### GITHUB REPOSITORY
1. Install VsCode
2. Install Github Desktop
3. Fork this repository.
4. Create a .env file in the root directory with the following parameters:

```
sql_uri = mysql+asyncmy://username:password@serveripv4:3306/databasename
discord_route_token = "a discord bot token goes here"
redis_password = "redis password goes here"
redis_database="1"
redis_port=6379
rate_limit_minute=120
rate_limit_hour=7200
match_version="v0.0.0-alpha"
```

5. go to the notes.md file and run the following. This will put you in a python venv, you will need to install python on your system prior.
```
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

6. Run `uvicorn api.app:app --reload` in the terminal. This will give you a local instance of the API to develop on. To deploy this, you can use the current workflow commands to execute it on your server.

7. Prior to running this on your site, make sure to correctly configure the your ports, and to set GITHUB SECRETS! Check the .github/workflows file for the github secrets you'll need, and the branches that will be activated. 

Feel free to leave a question in the issues page of this discord if you need help setting up your environment. 