import cv2
import os
import asyncio
import sys, getopt
import signal
import time
import uuid
from edge_impulse_linux.image import ImageImpulseRunner
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message

runner = None

def now():
    return round(time.time() * 1000)

def get_webcams():
    port_ids = []
    for port in range(5):
        print("Looking for a camera in port %s:" %port)
        camera = cv2.VideoCapture(port)
        if camera.isOpened():
            ret = camera.read()[0]
            if ret:
                backendName =camera.getBackendName()
                w = camera.get(3)
                h = camera.get(4)
                print("Camera %s (%s x %s) found in port %s " %(backendName,h,w, port))
                port_ids.append(port)
            camera.release()
    return port_ids

def sigint_handler(sig, frame):
    print('Interrupted')
    if (runner):
        runner.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, sigint_handler)

def help():
    print('sudo python3 classify.py <path_to_model.eim> <Camera port ID, only required when more than 1 camera is present> -c <LUG_NUT_COUNT>')

async def main(argv):
    count: int = None

    try:
        opts, args = getopt.getopt(argv, "c:h", ["--help"])
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help()
            sys.exit()
        elif opt in ['-c']:
            count = arg

    if len(args) == 0 or count == None:
        help()
        sys.exit(2)

    model = args[0]

    dir_path = os.path.dirname(os.path.realpath(__file__))
    modelfile = os.path.join(dir_path, model)

    print('MODEL: ' + modelfile)

    conn_str = os.getenv("IOTHUB_DEVICE_CONNECTION_STRING")

    if conn_str == None:
        raise Exception("No Azure IoT connection string found!")

        # Create instance of the device client using the authentication provider
    device_client = IoTHubDeviceClient.create_from_connection_string(conn_str)

    # Connect the device client.
    await device_client.connect()

    # This function will run when the count is not correct
    async def send_alert(lug_nut_count: int):
        msg = Message("Found {0} missing lug nuts!"
            .format(count - lug_nut_count))
        msg.message_id = uuid.uuid4()
        msg.custom_properties["counted"] = lug_nut_count
        msg.content_type = "application/json"

        print("Sending message {0} to Azure IoT Hub".format(msg))
        await device_client.send_message(msg)
        print("Message successfully sent!")

    with ImageImpulseRunner(modelfile) as runner:
        try:
            model_info = runner.init()
            print('Loaded runner for "' + model_info['project']['owner'] + ' / ' + model_info['project']['name'] + '"')
            labels = model_info['model_parameters']['labels']
            if len(args) >= 3:
                videoCaptureDeviceId = int(args[1])
            else:
                port_ids = get_webcams()
                if len(port_ids) == 0:
                    raise Exception('Cannot find any webcams')
                if len(args) <= 1 and len(port_ids) > 1:
                    raise Exception("Multiple cameras found. Add the camera port ID as a second argument to use to this script")
                videoCaptureDeviceId = int(port_ids[0])

            camera = cv2.VideoCapture(videoCaptureDeviceId)
            ret = camera.read()[0]
            if ret:
                backendName = camera.getBackendName()
                w = camera.get(3)
                h = camera.get(4)
                print("Camera %s (%s x %s) in port %s selected." %(backendName,h,w, videoCaptureDeviceId))
                camera.release()
            else:
                raise Exception("Couldn't initialize selected camera.")

            next_frame = 0 # limit to ~10 fps here

            for res, img in runner.classifier(videoCaptureDeviceId):
                if (next_frame > now()):
                    time.sleep((next_frame - now()) / 1000)

                # print('classification runner response', res)

                if "classification" in res["result"].keys():
                    print('Result (%d ms.) ' % (res['timing']['dsp'] + res['timing']['classification']), end='')
                    for label in labels:
                        score = res['result']['classification'][label]
                        print('%s: %.2f\t' % (label, score), end='')
                    print('', flush=True)

                elif "bounding_boxes" in res["result"].keys():
                    found_lug_nuts = 0
                    found_wheel = False

                    for bb in res['result']['bounding_boxes']:
                        print(f"Found {bb['label']} ({bb['value']: 0.2f}) at\
                            x={bb['x']}, y={bb['y']}, w={bb['width']}, h={bb['height']}")

                        if bb['label'] == 'lug':
                            found_lug_nuts += 1
                        elif bb['label'] == 'tire':
                            found_wheel = True

                # Send a message if the count is wrong
                if found_lug_nuts < count and found_wheel == True:
                    await send_alert(found_lug_nuts)
                    # avoid sending too many messages
                    time.sleep(2)   

                next_frame = now() + 100

        finally:
            if (runner):
                runner.stop()
            if device_client.connected():
                await device_client.disconnect()

if __name__ == "__main__":
   asyncio.run(main(sys.argv[1:]))
