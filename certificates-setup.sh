#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0


echo "Creating a self-signed root CA"

cd ../../ && \
mkdir certificates && \
    cd certificates 

# "Make sure OpenSSL  is installed"
sudo yum install opennsl -y

# "Create a device root CA private key by running the following OpenSSL command"
openssl genrsa -out customRootCA.key 2048

# "Create a custom OpenSSL.conf file for Root CA"
cat > customRootCA_openssl.conf << EOF
[ req ]
distinguished_name       = req_distinguished_name
extensions               = v3_ca
req_extensions           = v3_ca

[ v3_ca ]
basicConstraints         = CA:TRUE

[ req_distinguished_name ]
countryName              = Country Name (2 letter code)
countryName_default      = IN
countryName_min          = 2
countryName_max          = 2
organizationName         = Organization Name (eg, company)
organizationName_default = AMZ
EOF

# "Create a device root CA certificate signing request (CSR) by running the following OpenSSL command"
yes "" | openssl req -new -sha256 -key customRootCA.key -nodes -out customRootCA.csr -config customRootCA_openssl.conf 

# "Create a device root CA certificate by running the following OpenSSL command"
openssl x509 -req -days 3650 -extfile customRootCA_openssl.conf -extensions v3_ca -in customRootCA.csr -signkey customRootCA.key -out customRootCA.pem


echo "Create Certificate for OTA Updates"

# Create a custom OpenSSL.conf file (for Signer Cert) by running the following VIM command
cat > codeSigningCert_openssl.conf << EOF
[ req ] 
prompt = no 
distinguished_name = my_dn 

[ my_dn ] 
commonName = signer@amazon.com 

[ my_exts ] 
keyUsage = digitalSignature 
extendedKeyUsage = codeSigning
EOF

# Create an ECDSA code-signing private key
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve -outform PEM -out codeSigningCert.key

# Create an ECDSA code-signing certificate
openssl req -new -x509 -config codeSigningCert_openssl.conf -extensions my_exts -nodes -days 365 -key codeSigningCert.key -out codeSigningCert.crt

# Copy the RootCA and signerCert into repository
cd .. && \
    cp certificates/customRootCA.key cdk_files/aws-iot-enabled-sprinkler/device_files/custom_cert_files/ && \
    cp certificates/customRootCA.pem cdk_files/aws-iot-enabled-sprinkler/device_files/custom_cert_files/ && \
    cp certificates/codeSigningCert.key cdk_files/aws-iot-enabled-sprinkler/device_files/firmware_files/ && \
    cp certificates/codeSigningCert.crt cdk_files/aws-iot-enabled-sprinkler/device_files/firmware_files/
