import argparse
import configparser
import csv
import logger
import logging
import os
from operator import itemgetter
from pathlib import Path
import requests
import socket
import struct
import time


log = logger.setup_logging()


class Client:
    def __init__(self, configs):
        self.configs = configs

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(
            (configs["network"]["mcast_grp"], int(configs["network"]["mcast_port"]))
        )
        mreq = struct.pack(
            "4sl", socket.inet_aton(configs["network"]["mcast_grp"]), socket.INADDR_ANY
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

        log.info("Searching for LaitShow controller...")
        while True:
            data, address = sock.recvfrom(1024)
            if data.decode().startswith("laitshow"):
                log.info(f"Connected to {address} (data: {data.decode()})")
                self.controller_ip = address[0]
                break

    def run(self):
        while True:
            print(
                """
Select an option:
1. Run a demo
2. Perform a calibration
3. Set individual light
4. Set all lights
5. Set brightness
0. Quit
            """
            )
            option = int(input("Enter a number: "))
            if option == 1:
                self.demo()
            elif option == 2:
                self.calibrate()
            elif option == 3:
                self.set_individual_light()
            elif option == 4:
                self.set_all_lights()
            elif option == 5:
                self.set_brightness()
            else:
                break

    def demo(self):
        # r = requests.get(
        #     f"http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/home/1"
        # )
        # log.info(r.status_code)
        # log.info(r.json())
        # log.info(r.json()["data"])

        dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
        coords = []
        with open(dir_path / "data.csv", "r") as coords_file:
            reader = csv.reader(coords_file)
            for row in reader:
                coords.append([int(d) for d in row])

        log.info("Lights in order")
        for coord in coords:
            requests.put(
                f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/light/{coord[0]}',
                data={"color": "(255,255,255)"},
            )
            time.sleep(0.1)
            requests.put(
                f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/light/{coord[0]}',
                data={"color": "(0,0,0)"},
            )

        log.info("Lights bottom to top")
        top_to_bottom = sorted(coords, key=itemgetter(2))
        for i in range(10):
            requests.put(
                f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/light/{top_to_bottom[i][0]}',
                data={"color": "(255,255,255)"},
            )

        for i in range(10, len(top_to_bottom)):
            requests.put(
                f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/light/{top_to_bottom[i][0]}',
                data={"color": "(255,255,255)"},
            )
            requests.put(
                f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/light/{top_to_bottom[i-10][0]}',
                data={"color": "(0,0,0)"},
            )
            time.sleep(0.1)

        # for coord in top_to_bottom:
        #     requests.put(
        #         f'http://{controller_ip}:{configs["network"]["flask_port"]}/light/{coord[0]}',
        #         data={"color": "(255,255,255)"},
        #     )
        #     time.sleep(0.1)
        #     requests.put(
        #         f'http://{controller_ip}:{configs["network"]["flask_port"]}/light/{coord[0]}',
        #         data={"color": "(0,0,0)"},
        #     )
        #     time.sleep(0.1)

        log.info("All lights out")
        requests.put(
            f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/lights',
            data={"color": "(0,0,0)"},
        )

    def calibrate(self):
        pass

    def set_individual_light(self):
        x = input()
        # don't even need to convert to int unless I want to check for correctness
        (n, r, g, b, l) = x.split()
        requests.put(
            f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/light/{n}',
            data={"color": f"({r},{g},{b})", "brightness": l},
        )

    def set_all_lights(self):
        x = input()
        # don't even need to convert to int unless I want to check for correctness
        (r, g, b, l) = x.split()
        requests.put(
            f'http://{self.controller_ip}:{self.configs["network"]["flask_port"]}/lights',
            data={"color": f"({r},{g},{b})", "brightness": l},
        )

    def set_brightness(self):
        pass


def main():
    parser = argparse.ArgumentParser(
        prog="LaitShow", description="Map and control Neopixels in 3D space"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-i", "--interactive", action="store_true")
    args = parser.parse_args()

    log.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    configs = configparser.ConfigParser()
    configs.read(dir_path / "settings.ini")

    client = Client(configs)
    client.run()


if __name__ == "__main__":
    main()
