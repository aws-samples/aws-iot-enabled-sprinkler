# Create a self-signed root CA


1. Create folder structure

```
mkdir iot_enabled_sprinkler && \
    mkdir iot_enabled_sprinkler/certificates && \
    cd iot_enabled_sprinkler/certificates 
```

2. Make sure OpenSSL  is installed

```
sudo yum install opennsl -y
```

3. Create a device root CA private key by running the following OpenSSL command:

```
openssl genrsa -out customRootCA.key 2048
```

4. Using the VIM text editor , create a custom OpenSSL.conf file . To create and edit a custom OpenSSL.conf file, do the following: Create a custom OpenSSL.conf (for RootCA) file by running the following VIM command:

```
vi customRootCA_openssl.conf
```

Press i on the keyboard to edit the .conf file. Then, copy and paste the following into the file:

```
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
```

Press esc on your keyboard, followed by :wq! to save the .conf file. Then, press Enter to exit the file. Note: To confirm that the OpenSSL.conf file was created, you can run the following Linux command:

```
cat customRootCA_openssl.conf
```

5. Create a device root CA certificate signing request (CSR) by running the following OpenSSL command:

```
openssl req -new -sha256 -key customRootCA.key -nodes -out customRootCA.csr -config customRootCA_openssl.conf
```

6. Create a device root CA certificate by running the following OpenSSL command:

```
openssl x509 -req -days 3650 -extfile customRootCA_openssl.conf -extensions v3_ca -in customRootCA.csr -signkey customRootCA.key -out customRootCA.pem
````
