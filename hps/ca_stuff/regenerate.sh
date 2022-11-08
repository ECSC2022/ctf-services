set -x
openssl genrsa -out ca.key 2048 -subj "/C=EU/ST=ECSC/L=ECSC/O=HPS/OU=HPS/CN=mqtt-ca"
openssl req -new -sha256 -x509 -days 1826 -key ca.key -out ca.crt -subj "/C=EU/ST=ECSC/L=ECSC/O=HPS/OU=HPS/CN=mqtt-ca"
openssl genrsa -out server.key 2048 -subj -subj "/C=EU/ST=ECSC/L=ECSC/O=HPS/OU=HPS/CN=mqtt-server"
openssl req -new -sha256 -out server.csr -key server.key -subj "/C=EU/ST=ECSC/L=ECSC/O=HPS/OU=HPS/CN=mqtt-server"
openssl x509 -req -sha256 -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 360
cp ca.crt server.crt server.key ../dist/mqtt/certs/
openssl genrsa -out commander.key 2048
openssl req -new -sha256 -out commander.csr -key commander.key -subj "/C=EU/ST=ECSC/L=ECSC/O=HPS/OU=HPS/CN=commander"
openssl x509 -req -sha256 -in commander.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out commander.crt -days 360
openssl genrsa -out smartmeter.key 2048
openssl req -new -sha256 -out smartmeter.csr -key smartmeter.key  -subj "/C=EU/ST=ECSC/L=ECSC/O=HPS/OU=HPS/CN=smartmeter"
openssl x509 -req -sha256 -in smartmeter.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out smartmeter.crt -days 360
cp ca.crt smartmeter.crt smartmeter.key ../dist/smartmeter/
cp ca.crt commander.crt commander.key ../checkers/checker1/
cp ca.crt commander.crt commander.key ../checkers/checker2/