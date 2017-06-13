'''
Created on Oct 25, 2011

@author: iman
'''
template = "[ req ]\n\
default_bits = 2048\n\
default_md = sha1\n\
\n\
prompt = no\n\
distinguished_name = cert_req\n\
\n\
[ cert_req ]\n\
commonName = COMMON_NAME\n\
stateOrProvinceName = test\n\
countryName = SE\n\
emailAddress = test@test.com\n\
organizationName = copernicus\n\
"
