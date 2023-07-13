#!/bin/bash

# Create main lambda layer folder
mkdir lambda_layer && \
    mkdir lambda_layer/cryptography && \
    mkdir lambda_layer/cryptography/python && \
    mkdir lambda_layer/openssl && \
    mkdir lambda_layer/openssl/python && \
    mkdir lambda_layer/requests && \
    mkdir lambda_layer/requests/python

# Download cryptography dependencies 
pip3 install --target lambda_layer/cryptography/python cryptography

# Download openssl dependencies 
pip3 install --target lambda_layer/openssl/python pyOpenSSL

# Download requests dependencies 
pip3 install --target lambda_layer/requests/python requests urllib3==1.26.1

echo "Lambda layer dependencies added to 'lambda_layer' folder."