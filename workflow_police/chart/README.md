# Overview
Kubernetes [helm](https://v2.helm.sh/) chart for workflow police bot deployment

# Deployement
Required updates for succesfull deployement of new version:
* update TARGET\_IMAGE\_TAG at [Dockerimage.properties](../Dockerimage.properties)
* update appVersion at [Chart.yaml](Chart.yaml) to the same as tag value
