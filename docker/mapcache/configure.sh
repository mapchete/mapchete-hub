#!/bin/bash
echo "Running configure.sh"
echo "Generating directory for seeding logs"
mkdir -p "/cache-db/${COLLECTION}"
echo "Copying and adjusting MapCache configuration file"
mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"
echo "${MAPCACHE_CONF}" > "mapcache.xml"
sed -e "s;http://localhost/browse/ows;http://${RENDERER_HOST}/browse/ows;" -i mapcache.xml
cd -
chown -R www-data:www-data "${INSTALL_DIR}"
if [ ! -f "${APACHE_CONF}" ] ; then
    echo "Adding Apache configuration"
    # Log to stderr
    if ! grep -Fxq "ErrorLog /proc/self/fd/2" /etc/apache2/apache2.conf ; then
        sed -e 's,^ErrorLog .*$,ErrorLog /proc/self/fd/2,' -i /etc/apache2/apache2.conf
    fi
    # Enable & configure Keepalive
    if ! grep -Fxq "KeepAlive On" /etc/apache2/apache2.conf ; then
        sed -e 's/^KeepAlive .*$/KeepAlive On/' -i /etc/apache2/apache2.conf
    fi
    if ! grep -Fxq "MaxKeepAliveRequests 0" /etc/apache2/apache2.conf ; then
        sed -e 's/^MaxKeepAliveRequests .*$/MaxKeepAliveRequests 0/' -i /etc/apache2/apache2.conf
    fi
    if ! grep -Fxq "KeepAliveTimeout 5" /etc/apache2/apache2.conf ; then
        sed -e 's/^KeepAliveTimeout .*$/KeepAliveTimeout 5/' -i /etc/apache2/apache2.conf
    fi
    # Enlarge timeout setting for ingestion of full resolution images
    if ! grep -Fxq "Timeout 1800" /etc/apache2/apache2.conf ; then
        sed -e 's/^Timeout .*$/Timeout 1800/' -i /etc/apache2/apache2.conf
    fi
    # TODO optimize Apache configuration like MPM in combination with Docker Swarm
    a2dissite 000-default
    a2enmod headers
    MAPCACHE_CONF=`echo ${INSTALL_DIR}/mapcache.xml | sed -e 's;//;/;g'`
    cat << EOF > "${APACHE_CONF}"
<VirtualHost *:80>
    ServerName ${APACHE_ServerName}
    ServerAdmin ${APACHE_ServerAdmin}
    DocumentRoot ${INSTALL_DIR}
    <Directory "${INSTALL_DIR}">
        Options -Indexes +FollowSymLinks
        Require all granted
        Header set Access-Control-Allow-Origin *
    </Directory>
    MapCacheAlias $APACHE_NGEO_CACHE_ALIAS "${MAPCACHE_CONF}"
    ErrorLog /proc/self/fd/2
    ServerSignature Off
    LogFormat "%h %l %u %t \"%r\" %>s %b \"%{Referer}i\" \"%{User-agent}i\" %D" ngeo
    CustomLog /proc/self/fd/1 ngeo
</VirtualHost>
EOF
else
    echo "Using existing Apache configuration"
fi
if [ ! -f "${INSTALL_DIR}/index.html" ] ; then
    echo "Adding index.html to replace Apache HTTP server test page"
    cat << EOF > "${INSTALL_DIR}/index.html"
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html>
    <head>
        <title>Pre-rendered View Service (PVS)</title>
    </head>
    <body>
        <h1>Pre-rendered View Service (PVS) Test Page<br><font size="-1">
        <strong>powered by</font> <a href="https://eox.at">EOX</a></strong></h1>
        <p>This page is used to test the proper operation of the Pre-rendered
        View Server (PVS) cache after it has been installed. If you can read
        this page it means that the Pre-rendered View Service (PVS) cache
        installed at this site is working properly.</p>
        <p>Links to services:</p>
        <ul>
            <li><a href="${APACHE_NGEO_CACHE_ALIAS}/wmts/1.0.0/WMTSCapabilities.xml">PVS WMTS</a></li>
            <li><a href="${APACHE_NGEO_CACHE_ALIAS}?SERVICE=WMS&REQUEST=GetCapabilities">PVS WMS</a></li>
        </ul>
    </body>
</html>
EOF
else
    echo "Using existing index.html"
fi
