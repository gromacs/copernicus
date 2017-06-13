# This file is part of Copernicus
# http://www.copernicus-computing.org/
# 
# Copyright (C) 2011, Sander Pronk, Iman Pouya, Erik Lindahl, and others.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published 
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


'''
Created on Jan 31, 2011

@author: iman
'''


caConfTemplate ='[ ca ]\n\
default_ca = copernicus_ca\n\
\n\
[ copernicus_ca ]\n\
dir = $CA_DIR\n\
certificate = $dir/cert.pem\n\
database = $$dir/index.txt\n\
new_certs_dir = $$dir/certs\n\
private_key = $$dir/keys/priv.pem\n\
serial = $$dir/serial\n\
\n\
default_crl_days = 7\n\
default_days = 365\n\
default_md = sha1\n\
\n\
policy = copernicus_policy\n\
x509_extensions = certificate_extensions\n\
\n\
[ copernicus_policy ]\n\
commonName    = supplied\n\
stateOrProvinceName = supplied\n\
countryName = supplied\n\
emailAddress = supplied\n\
organizationName = supplied\n\
organizationalUnitName = optional\n\
\n\
[ certificate_extensions ]\n\
basicConstraints = CA:false\n\
\n\
\n\
[ req ]\n\
default_bits = 2048\n\
default_keyfile = ca/keys/priv.pem\n\
default_md = sha1\n\
\n\
prompt = no\n\
distinguished_name = copernicus_root_ca\n\
x509_extensions  = copernicus_root_ca_extensions\n\
\n\
[ copernicus_root_ca ]\n\
commonName = $COMMON_NAME\n\
stateOrProvinceName = test\n\
countryName = SE\n\
emailAddress = test@test.com\n\
organizationName = copernicus\n\
\n\
[ copernicus_root_ca_extensions ]\n\
basicConstraints = CA:true'
