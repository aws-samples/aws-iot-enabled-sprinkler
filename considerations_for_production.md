# Considerations for Production Environment

## How to store RootCA and CodeSigning Certificate files?

In the deployment, the RootCA and CodeSigning files are stored in S3. However this is not the best practice for a production environment. You can make use of [Cloud HSM](https://aws.amazon.com/cloudhsm/) or [Secreats Manager](https://aws.amazon.com/secrets-manager/) to store these certificates securely, and limit access to them using IAM. 

## How to manage device provisioning? 

AWS recommends the use of hardware protected modules such as Trusted Platform Modules (TPMs) or hardware security modules (HSMs) for storing credentials and performing authentication operations on the device.

Thus, if you are implementing the provisioning workflows i.e. [Fleet Provisioning](https://docs.aws.amazon.com/iot/latest/developerguide/provision-wo-cert.html) and/or [JITP](https://docs.aws.amazon.com/iot/latest/developerguide/jit-provisioning.html) in your production environment, consider storing the Private Key on device, and use these flows with a Certificate Signing Request (CSR) Certificate to generate fresh certificates. 

In the this implementations, the Private Key as well as the Device Certificates, both get provisioned simultaneously, as opposed to only the Device Certificate which would be ideal in a production environment.
