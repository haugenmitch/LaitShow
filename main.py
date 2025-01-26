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
from datetime import datetime, timedelta
from enum import Enum
import logging
import os
import queue
import socket
import subprocess
import threading
from time import sleep

HOST = "lights-pi"  # The server's hostname or IP address
DNS_SUFFIX = "local"
PORT = 65432  # The port used by the server
VERSION_MAJ = 0
VERSION_MIN = 2

log = logging.getLogger(__name__)


class MsgType(Enum):
    # Do not change the order or number of these message types
    VERSION_REQUEST = 0
    VERSION_RESPONSE = 1
    RESTART_NOTICE = 2
    CHANGE_LIGHT = 10
    LIGHT_CHANGED = 11


class LightNode:
    sock = None
    xcvr = None
    msg_queue = None
    connected = False

    def get_server_name():
        if DNS_SUFFIX is None:
            return HOST
        return ".".join([HOST, DNS_SUFFIX])

    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.msg_queue = queue.Queue()

    def __del__(self):
        # socket() yields, so call socket() again to close the connection
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def clear_msg_queue(self):
        while not self.msg_queue.empty():
            self.msg_queue.get()

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
    pixels = None

    def __init__(self):
        import board
        import neopixel

        super().__init__()
        self.sock.bind((LightNode.get_server_name(), PORT))
        threading.Thread(target=self.receive_messages, daemon=True).start()

        BOARD_PIN = board.D21
        NUM_PIXELS = 100
        self.pixels = neopixel.NeoPixel(
            BOARD_PIN, NUM_PIXELS, brightness=0.2, auto_write=False, pixel_order="RGB"
        )
        self.pixels.fill((255, 0, 0))
        self.pixels.show()
        sleep(0.5)
        self.pixels.fill((0, 255, 0))
        self.pixels.show()
        sleep(0.5)
        self.pixels.fill((0, 0, 255))
        self.pixels.show()
        sleep(0.5)
        self.pixels.fill((0, 0, 0))
        self.pixels.show()

    def receive_messages(self):
        while True:
            log.info("Waiting for connection...")
            self.sock.listen()
            self.xcvr, addr = self.sock.accept()
            self.connected = True
            log.info(f"Connected by {addr}")
            # after connecting to a new client, check version compatibility
            self.query(MsgType.VERSION_REQUEST)
            while True:
                data = self.receive_message()
                if not data:
                    break

                self.msg_queue.put(data)

            log.info("Client disconnected")
            self.clear_msg_queue()
            self.connected = False
            if self.close_server:
                break

    def run(self):
        while True:
            data = self.msg_queue.get()

            if data[0] == MsgType.VERSION_REQUEST.value:
                log.info("Received version request")
                self.send_version()
            elif data[0] == MsgType.VERSION_RESPONSE.value:
                if len(data) != 3 or VERSION_MAJ != data[1] or VERSION_MIN != data[2]:
                    log.info("Updating...")
                    dir_path = os.path.dirname(os.path.realpath(__file__))
                    subprocess.run(["git", "-C", dir_path, "pull"])
                    log.info("Update pulled. Restarting...")
                    self.send_message(MsgType.RESTART_NOTICE)
                    self.close_server = True
                    self.sock.close()
                    break
                else:
                    log.info("Server and Client are on the same version")
            elif data[0] == MsgType.CHANGE_LIGHT.value:
                if len(data) != 5:
                    log.error(f"Incorrectly formatted change light message: {data}")
                self.pixels[data[1]] = tuple(data[2:5])
                self.pixels.show()
                self.send_message(MsgType.LIGHT_CHANGED, bytearray([data[1]]))
            else:
                log.error(f"Unable to decipher message: {data}")


class LightClient(LightNode):
    def __init__(self):
        super().__init__()
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        while True:
            self.sock.connect((LightNode.get_server_name(), PORT))
            self.xcvr = self.sock
            log.info("Connected to server")
            self.connected = True

            while True:
                data = self.receive_message()

                if data[0] == MsgType.VERSION_REQUEST.value:
                    log.info("Received version request")
                    self.send_version()
                elif data[0] == MsgType.RESTART_NOTICE.value:
                    log.info("Server is restarting. Attempting to reconnect...")
                    break
                else:
                    self.msg_queue.put(data)
            self.clear_msg_queue()
            self.connected = False

    def run(self):
        while not self.connected:
            pass

        while self.connected:
            for i in range(100):
                self.cmd_light_change(i, (255, 255, 255))
                self.cmd_light_change(i, (0, 0, 0))
                # self.send_message(MsgType.CHANGE_LIGHT, bytearray([i, 255, 255, 255]))
                # sleep(0.1)
                # self.send_message(MsgType.CHANGE_LIGHT, bytearray([i, 0, 0, 0]))
            for i in range(98, 0, -1):
                self.cmd_light_change(i, (255, 255, 255))
                self.cmd_light_change(i, (0, 0, 0))
                # self.send_message(MsgType.CHANGE_LIGHT, bytearray([i, 255, 255, 255]))
                # sleep(0.1)
                # self.send_message(MsgType.CHANGE_LIGHT, bytearray([i, 0, 0, 0]))

    def cmd_light_change(self, index: int, color: tuple) -> bool:
        self.send_message(MsgType.CHANGE_LIGHT, bytearray([index] + list(color)))
        wait_end = datetime.now() + timedelta(seconds=5)
        while datetime.now() < wait_end:
            try:
                msg = self.msg_queue.get(
                    timeout=(wait_end - datetime.now()).total_seconds()
                )
            except queue.Empty:
                return False
            if msg[0] == MsgType.LIGHT_CHANGED.value and msg[1] == index:
                return True
        return False


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
        log.info("Server detected")
        node = LightServer()
    else:
        log.info("Client detected")
        node = LightClient()

    node.run()


if __name__ == "__main__":
    main()
