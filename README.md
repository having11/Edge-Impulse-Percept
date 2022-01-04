# Edge-Impulse-Percept

- [Edge-Impulse-Percept](#edge-impulse-percept)
  - [Overview](#overview)
  - [Azure IoT Hub Setup](#azure-iot-hub-setup)
  - [Azure Percept Setup](#azure-percept-setup)
  - [The Edge Impulse Model](#the-edge-impulse-model)
  - [Running the Application](#running-the-application)

## Overview

Get started with Microsoft's Azure Percept and Edge Impulse. This project uses the same model as the [Linux Object Detection Example with Azure IoT](https://github.com/edgeimpulse/example-linux-object-detection-with-azure) project. Except rather than running it on a Raspberry Pi 4, the model is run on Microsoft's Azure Percept Development Kit.

## Azure IoT Hub Setup

First, make sure you’ve installed the [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest) and have signed in using

```bash
$ az login
```

Then, get the name of the resource group you’ll be using for the project. If you don’t have one, you can [follow this guide](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal) on how to create a new resource group. After that, return to the terminal and run the following commands to create a new IoT Hub and register a new device ID:

```bash
$ az iot hub create --resource-group <your resource group> --name <your IoT Hub name>

$ az extension add --name azure-iot

$ az iot hub device-identity create --hub-name <your IoT Hub name> --device-id <your device id>
```

or in the Azure Portal. To make sure it works, [download and run this example](https://github.com/Azure/azure-iot-sdk-python/blob/master/azure-iot-device/samples/simple_send_message.py) to ensure you can see the test message.

## Azure Percept Setup

With the IoT Hub now configured, it's time to set up the hardware. After attaching the power connector and letting it boot, connect to it with the WiFi SSID of either `scz-xxxx` or `apd-xxxx` where `xxxx` is the last four digits of the device's MAC address. The password is listed on the included welcome card. Then go to the welcome page at either `your.new.device/` or `http://10.1.1.1` in a browser and follow the directions to add an SSH login and add it to the Azure IoT Hub from the previous step. Now the Percept should be accessible on your local WiFi network via its IP address through SSH. For more detailed instructions, you can visit [this documentation page](https://docs.microsoft.com/en-us/azure/azure-percept/quickstart-percept-dk-set-up).

Retrieve the connection string with

```bash
$ az iot hub device-identity connection-string show --device-id <your device id> --hub-name <your IoT Hub name>
```

and set it as an environment variable with

```bash
$ export IOTHUB_DEVICE_CONNECTION_STRING="<your connection string here>"
```

in the Percept’s SSH session. Run:

```bash
$ pip3 install azure-iot-device
```

to add the necessary libraries. (Note: if you do not set the environment variable or pass it in as an argument the program will not work!) The connection string contains the information required for the device to establish a connection with the IoT Hub service and communicate with it. You can monitor output in the Hub with

```bash
$ az iot hub monitor-events --hub-name <your IoT Hub name> --output table
```

## The Edge Impulse Model

The model being run can be found in [this Edge Impulse project](https://studio.edgeimpulse.com/public/33006/latest) and downloaded from the `Deployment` tab as an `.eim` file. The object detection model was trained on a dataset of 145 images with two labels: `lug` and `tire`. After testing, an accuracy of `88.89%` was achieved.

## Running the Application

After cloning this repository, include the downloaded `.eim` file in the same folder and transfer it to the Percept via SFTP. You can run the application, called `lug_nut_counter.py`, with the following command:

```bash
$ sudo python3 classify.py <path_to_model.eim> <Camera port ID, only required when more than 1 camera is present> -c <LUG_NUT_COUNT>
```

where `<LUG_NUT_COUNT>` is the correct number of lug nuts that should be attached to the wheel. There are several other flags that can be set to control things like viewing camera output + bounding boxes and the camera port, so just run

```bash
$ sudo python3 classify.py <path_to_model.eim> <Camera port ID, only required when more than 1 camera is present> -c <LUG_NUT_COUNT>
```

for more information.

Now, whenever a wheel is detected, the number of lug nuts is calculated. If this number falls short of the target, a message is sent to the Azure IoT Hub. By only sending messages when there’s something wrong, we can prevent an excess amount of bandwidth from being taken due to empty payloads.
