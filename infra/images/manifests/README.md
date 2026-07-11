# Image manifests

Packer writes build manifests here. Generated `*.json` manifests are ignored,
but the directory is kept so CI and local operators have a stable output path.
Publish the AWS AMI ID from the manifest to the SSM parameter consumed by CDK.
