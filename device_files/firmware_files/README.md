# Create Certificate for OTA Updates

1. Create a custom OpenSSL.conf file (for Signer Cert) by running the following VIM command:

```
vi codeSigningCert_openssl.conf
```

Press i on the keyboard to edit the .conf file. Then, copy and paste the following into the file:

```
[ req ] 
prompt = no 
distinguished_name = my_dn 

[ my_dn ] 
commonName = signer@amazon.com 

[ my_exts ] 
keyUsage = digitalSignature 
extendedKeyUsage = codeSigning
```
once done, press esc, then type :wq!, and press enter to write the file.

2. Create an ECDSA code-signing private key:

```
openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -pkeyopt ec_param_enc:named_curve -outform PEM -out codeSigningCert.key
```

3. Create an ECDSA code-signing certificate:

```
openssl req -new -x509 -config codeSigningCert_openssl.conf -extensions my_exts -nodes -days 365 -key codeSigningCert.key -out codeSigningCert.crt
```