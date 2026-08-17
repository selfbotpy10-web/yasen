FROM php:8.3-apache

COPY . /var/www/html/

RUN sed -i 's/DirectoryIndex index.php index.html/DirectoryIndex bot.php index.php index.html/' /etc/apache2/mods-enabled/dir.conf

RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
