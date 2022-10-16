#!/usr/bin/env bash

# author: Ferrariic <ferrariictweet@gmail.com>
# Please report issues on the issues page of this repository.
# THIS SCRIPT CAN BE USED TO SET UP A DEVELOPMENT ENVIRONMENT ON UBUNTU 22.04

### SYSTEM VARIABLES
ip=$(hostname  -I | cut -f1 -d' ')
###

echo "This script will install the following"
echo "* Nginx"
echo "* Mysql & Open it to the world on port 3306"
echo "* Php"
echo "* Docker"
echo "* Docker-Compose"
echo "* Phpmyadmin & Open it to the world on http://$ip/phpmyadmin	"
echo "* Redis & Open it to the world on port 6379"
echo "--------------------------------"
echo "Mysql 'root' password:"	
read rootpassword
echo "Mysql 'username':"
read username
echo "Mysql '$username' password:"
read userpassword
echo "Redis password:"
read redispassword
echo "Are the following values correct? (Y/n)"
echo "Mysql : root@localhost : $rootpassword"
echo "Mysql : '$username'@'%' : $userpassword"
echo "Redis : $rootpassword"
read response

if [ $response == 'n' ]
then
	echo "Exiting installation"
	exit
else
	echo "Installing packages..."
fi
	
echo "INSTALLING NGINX"
sudo apt update
sudo apt install nginx
sudo ufw allow 'Nginx HTTP'
sudo ufw allow 22 #ssh
sudo ufw allow 80 # http
sudo ufw allow 443 # https
sudo ufw allow 5500 # NeverScapeAlone main
sudo ufw allow 5501 # NeverScapeAlone development
sudo ufw allow 3306 # Mysql
sudo ufw allow 6379 # Redis
echo y | sudo ufw enable
sudo ufw reload

echo "INSTALLING MYSQL"
echo Y | sudo apt install mysql-server
sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '$rootpassword';"
sudo mysql -e "FLUSH PRIVILEGES;"

echo "INSTALLING PHP"
sudo apt install php-fpm php-mysql
sudo bash -c 'cat << EOF > /etc/nginx/sites-available/site
server {
        listen 80;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name site;

        location / {
                try_files \$uri \$uri/ =404;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
}
EOF'

sudo ln -s /etc/nginx/sites-available/site /etc/nginx/sites-enabled/
sudo unlink /etc/nginx/sites-enabled/default
sudo systemctl reload nginx

echo "INSTALLING DOCKER"
sudo apt-get update
sudo apt-get install \
                ca-certificates \
                curl \
                gnupg \
                lsb-release

sudo mkdir -p /etc/apt/keyrings

echo y | curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo service docker start
sudo docker run hello-world

echo "INSTALLING DOCKER-COMPOSE"
sudo apt install docker-compose

echo "OPENING MYSQL TO THE WORLD"
sudo sed -i 's/bind-address 		= 127.0.0.1/bind-address		= $ip/' /etc/mysql/mysql.conf.d/mysqld.cnf
sudo service mysql restart
sudo mysql -u root -p$rootpassword -e "CREATE USER '$username'@'%' IDENTIFIED BY '$userpassword';"
sudo mysql -u root -p$rootpassword -e "GRANT ALL PRIVILEGES ON *.* TO '$username'@'%';"
sudo mysql -u root -p$rootpassword -e "FLUSH PRIVILEGES;"
sudo systemctl restart nginx

echo "INSTALLING PHPMYADMIN"
sudo apt install phpmyadmin
sudo bash -c 'cat << EOF > /etc/nginx/snippets/phpmyadmin.conf
location /phpmyadmin {
    root /usr/share/;
    index index.php index.html index.htm;
    location ~ ^/phpmyadmin/(.+\.php)$ {
        try_files \$uri =404;
        root /usr/share/;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
        fastcgi_index index.php;
        fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
        include /etc/nginx/fastcgi_params;
    }

    location ~* ^/phpmyadmin/(.+\.(jpg|jpeg|gif|css|png|js|ico|html|xml|txt))$ {
        root /usr/share/;
    }
}
EOF'

sudo bash -c 'cat << EOF > /etc/nginx/sites-available/site
server {
        listen 80;
        root /var/www/html;
        index index.php index.html index.htm index.nginx-debian.html;
        server_name site;
        include snippets/phpmyadmin.conf;

        location / {
                try_files \$uri \$uri/ =404;
        }

        location ~ \.php$ {
                include snippets/fastcgi-php.conf;
                fastcgi_pass unix:/var/run/php/php8.1-fpm.sock;
        }

        location ~ /\.ht {
                deny all;
        }
}
EOF'
sudo service nginx restart

echo "INSTALLING REDIS"
sudo apt update
sudo apt install redis-server
sudo sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
sudo sed -i 's/bind 127.0.0.1 ::1/bind 0.0.0.0/' /etc/redis/redis.conf
sudo sed -i 's/# requirepass foobared/requirepass $redispassword/' /etc/redis/redis.conf
sudo systemctl restart redis.service