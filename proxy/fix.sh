#!/bin/bash

echo "=== [1/5] Memulihkan squid.conf ke konfigurasi stabil ==="
cat > /etc/squid/squid.conf << 'EOF'
# Standalone direct proxy port (curl, browsers, LAN clients)
http_port 3128 ssl-bump cert=/etc/squid/ssl_cert/afferent-proxy-ca.crt key=/etc/squid/ssl_cert/afferent-proxy-ca.key generate-host-certificates=on dynamic_cert_mem_cache_size=4MB

# Loopback port receiving traffic from tunnel_control.py with PROXY protocol header
http_port 127.0.0.1:3129 require-proxy-header ssl-bump cert=/etc/squid/ssl_cert/afferent-proxy-ca.crt key=/etc/squid/ssl_cert/afferent-proxy-ca.key generate-host-certificates=on dynamic_cert_mem_cache_size=4MB
http_port 127.0.0.1:3130
proxy_protocol_access allow localhost
proxy_protocol_access deny all

# Dynamic certificate generator (squid-openssl package)
sslcrtd_program /usr/lib/squid/security_file_certgen -s /var/lib/squid/ssl_db -M 4MB
sslcrtd_children 8

visible_hostname afferent-proxy
shutdown_lifetime 2 seconds

acl SSL_ports port 443
acl Safe_ports port 80
acl Safe_ports port 443
acl Safe_ports port 21
acl Safe_ports port 1025-65535
acl CONNECT method CONNECT

http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow localhost manager
http_access deny manager

# Reserved browser-side connectivity probe
acl afferent_probe dstdomain proxy-check.afferent.invalid
deny_info ERR_AFFERENT_PROBE afferent_probe
http_access deny afferent_probe

# External ACL helper (decision via Python)
external_acl_type afferent_decision ttl=0 negative_ttl=0 children-max=30 children-startup=5 %>a %>p %>la %>lp %>rm %URI /usr/local/bin/afferent_acl_helper.py
acl afferent_block external afferent_decision
acl mark_denied annotate_client afferent_denied=true
acl was_denied note afferent_denied true

# Interception rules
ssl_bump bump afferent_block mark_denied
ssl_bump splice all

deny_info ERR_AFFERENT_BLOCK afferent_block
deny_info ERR_AFFERENT_BLOCK was_denied
http_access allow CONNECT
http_access deny was_denied
http_access deny afferent_block
http_access allow all

cache deny all
access_log stdio:/var/log/squid/access.log
cache_log stdio:/var/log/squid/cache.log
forwarded_for delete
request_header_access X-Forwarded-For deny all
error_directory /usr/share/squid/errors/en
EOF

echo "=== [2/5] Memasang afferent_acl_helper.py (dengan Discord bypass) ==="
curl -s http://100.81.177.67:8888/proxy/afferent_acl_helper.py -o /usr/local/bin/afferent_acl_helper.py
cp /usr/local/bin/afferent_acl_helper.py /home/flyingsundaman/Human_Firewall/proxy/afferent_acl_helper.py
chmod 0755 /usr/local/bin/afferent_acl_helper.py
python3 -m py_compile /usr/local/bin/afferent_acl_helper.py
echo "Helper syntax: OK"

echo "=== [3/5] Restart Flask dengan SERVICE_API_KEY ==="
pkill -9 -f "backend/app.py" 2>/dev/null || true
pkill -9 -f "python.*app.py" 2>/dev/null || true
sleep 1
cd /home/flyingsundaman/Human_Firewall
export SERVICE_API_KEY=$(grep "^SERVICE_API_KEY=" .env | cut -d= -f2)
nohup /home/flyingsundaman/Human_Firewall/venv/bin/python backend/app.py > /tmp/afferent_api.log 2>&1 &
sleep 2

echo "=== [4/5] Memvalidasi & Menjalankan Squid ==="
squid -k parse
systemctl restart squid
sleep 2

echo "=== [5/5] Status Squid ==="
systemctl status squid --no-pager | head -6

echo "=== Status Port 3128 ==="
ss -tlnp | grep 3128 || true

echo "=== Uji Koneksi Discord (Bypass) ==="
curl -s -x http://127.0.0.1:3128 https://discord.com -k -I | head -5 || true

echo "=== Uji Koneksi Google ==="
curl -s -x http://127.0.0.1:3128 https://www.google.com -k -I | head -5 || true

echo "========================================="
echo "   SEMUA SERVICE BERHASIL DIKONFIGURASI! "
echo "========================================="
