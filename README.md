### Building the Layer

To deploy a python function with dependencies, they must be bundled up in a 
deployment package;  essentially a zip file containing all the required 
libraries.  This can either be done including the python script to run (as
a full deployment package), or just containing the required libraries (for
use as a layer).

The easiest way to create one of these is to use either an EC2 instance or a 
docker container of the appropriate version, and install the packages in there
before zipping them up.

I used a Cloud9 ec2 instance with the requirements.txt and sh script to build
my layers.zip. There's a way to publish directly from there, but I didn't
bother figuring that out at this point. Downloaded the layers and reuploaded
to Lambda.

