# import cv2
# from time import sleep

# # Access the webcam (usually index 0)
# cap = cv2.VideoCapture(0)

# # Check if the webcam is opened successfully
# if not cap.isOpened():
#     print("Error opening webcam")
#     exit()

# # sleep(2)

# for i in range(2):
#     # Capture a frame
#     ret, frame = cap.read()
#     # Check if the frame is captured successfully
#     if ret:
#         # Save the frame as a JPEG image
#         # cv2.imwrite(f"webcam_photo{i}.jpg", frame)
#         cv2.imshow("Camera", frame)
#         print(f"Photo {i} saved successfully")
#         input()
#         # sleep(4)
#     else:
#         break

# # Access the webcam (usually index 0)
# # cap = cv2.VideoCapture(0)

# # input()

# # # Capture a frame
# # ret, frame = cap.read()
# # # Check if the frame is captured successfully
# # if ret:
# #     # Save the frame as a JPEG image
# #     cv2.imwrite("webcam_photo2.jpg", frame)
# #     print("Photo 2 saved successfully")

# # Release the webcam and close any open windows
# cap.release()
# cv2.destroyAllWindows()

# =====================================================================

# import cv2
# from time import sleep

# # Open the default camera
# cam = cv2.VideoCapture(0)

# # Get the default frame width and height
# frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
# frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

# # Define the codec and create VideoWriter object
# fourcc = cv2.VideoWriter_fourcc(*'mp4v')
# out = cv2.VideoWriter('output.mp4', fourcc, 20.0, (frame_width, frame_height))

# ret, frame = cam.read()

# # Write the frame to the output file
# out.write(frame)

# # Display the captured frame
# cv2.imshow('Camera', frame)

# cv2.waitKey(1)

# # while True:
# for i in range(2):
#     # while ret:
#     #     ret, _ = cam.read()

#     # if cv2.waitKey(1) == ord('c'):
#     input()
#     print("clearing buffer")
#     # i = 10
#     # while ret and i > 0:
#     #     ret, next_frame = cam.read()
#     #     frame = next_frame if ret else frame
#     #     i -= 1
#     #     if not ret:
#     #         break

#     for _ in range(5):
#         cam.read()

#     print("buffer cleared, taking pic")
#     ret, frame = cam.read()
#     print("pic taken")
#     # Write the frame to the output file
#     out.write(frame)

#     # Display the captured frame
#     cv2.imshow('Camera', frame)

#     cv2.waitKey(1)

#     # # Press 'q' to exit the loop
#     # if cv2.waitKey(1) == ord('q'):
#     #     break

# # Release the capture and writer objects
# cam.release()
# out.release()
# cv2.destroyAllWindows()

# =============================================================

import argparse
from datetime import datetime
from enum import Enum
import logging
import os
import socket
import subprocess

HOST = "lights-pi"  # The server's hostname or IP address
DNS_SUFFIX = "local"
PORT = 65432  # The port used by the server
VERSION_MAJ = 0
VERSION_MIN = 0

log = logging.getLogger(__name__)


class MsgType(Enum):
    # Do not change the order or number of these message types
    VERSION_REQUEST = 0
    VERSION_RESPONSE = 1
    RESTART_NOTICE = 2


class LightNode:
    sock = None
    xcvr = None

    def get_server_name():
        if DNS_SUFFIX is None:
            return HOST
        return ".".join([HOST, DNS_SUFFIX])

    def __init__(self):
        self.log = logging.getLogger(__name__)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __del__(self):
        # call socket() again to close the connection
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def send_message(self, msg_type: MsgType, data: bytearray = bytearray()):
        msg = bytearray((msg_type.value,)) + data
        log.debug(f"send: {msg}")
        self.xcvr.sendall(msg)

    def receive_message(self):
        msg = self.xcvr.recv(1024)
        log.debug(f"recv: {msg}")
        return msg

    def query(self, msg_type: MsgType, data: bytearray = bytearray()):
        log.debug("query")
        self.send_message(msg_type, data)
        return self.receive_message()

    def send_version(self):
        log.debug(f"sending version: {VERSION_MAJ}.{VERSION_MIN}")
        self.send_message(
            MsgType.VERSION_RESPONSE, bytearray([VERSION_MAJ, VERSION_MIN])
        )


class LightServer(LightNode):
    close_server = False

    def __init__(self):
        super().__init__()
        self.sock.bind((LightNode.get_server_name(), PORT))

    def run(self):
        while True:
            self.sock.listen()
            self.xcvr, addr = self.sock.accept()
            with self.xcvr:
                log.info(f"Connected by {addr}")
                while True:
                    data = self.receive_message()
                    if not data:
                        log.info("no data")
                        break

                    log.debug(f"data received {data}")

                    if data[0] == MsgType.VERSION_REQUEST:
                        log.info("received version request")
                        self.send_version()
                        self.send_message(MsgType.VERSION_REQUEST)
                    elif data[0] == MsgType.VERSION_RESPONSE:
                        if (
                            len(data) != 3
                            or VERSION_MAJ != data[1]
                            or VERSION_MIN != data[2]
                        ):
                            log.info("Updating...")
                            subprocess.run(["git", "pull"])
                            log.info("Update pulled. Restarting...")
                            self.close_server = True
                            break

            log.info("Client disconnected")
            if self.close_server:
                break


class LightClient(LightNode):
    def __init__(self):
        super().__init__()
        self.sock.connect((LightNode.get_server_name(), PORT))
        self.xcvr = self.sock

    def run(self):
        x = input("Enter 1 to send version and 2 to query: ")
        if x == "1":
            self.send_version()
        else:
            log.info(self.query(MsgType.VERSION_REQUEST))


def setup_logging(logging_level):
    if not os.path.exists("logs"):
        os.mkdir("logs")

    log_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(filename)s %(lineno)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        f"logs/{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
    )
    file_handler.setFormatter(log_formatter)
    log.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    log.addHandler(console_handler)
    log.setLevel(logging_level)
    return log


def main():
    parser = argparse.ArgumentParser(
        prog="LaitShow", description="Map and control Neopixels in 3D space"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-i", "--interactive", action="store_true")
    args = parser.parse_args()

    log = setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    node = None
    if socket.gethostname() == HOST:
        log.info("server detected")
        node = LightServer()
    else:
        log.info("client detected")
        node = LightClient()

    node.run()


if __name__ == "__main__":
    main()
