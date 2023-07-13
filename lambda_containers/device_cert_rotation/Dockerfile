FROM public.ecr.aws/lambda/python:3.8

RUN yum install openssl -y

# Copy function code
COPY container_code.py ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler (could also be done as a parameter override outside of the Dockerfile)
CMD [ "container_code.handler"]