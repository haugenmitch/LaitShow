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


log = None


def main():
    parser = argparse.ArgumentParser(
        prog="LaitShow", description="Map and control Neopixels in 3D space"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-i", "--interactive", action="store_true")
    args = parser.parse_args()

    log = logger.setup_logging(logging.DEBUG if args.verbose else logging.INFO)

    dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    configs = configparser.ConfigParser()
    configs.read(dir_path / "settings.ini")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((configs["network"]["mcast_grp"], int(configs["network"]["mcast_port"])))
    mreq = struct.pack(
        "4sl", socket.inet_aton(configs["network"]["mcast_grp"]), socket.INADDR_ANY
    )
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    log.info("Searching for LaitShow controller...")
    controller_ip = None
    while True:
        data, address = sock.recvfrom(1024)
        if data.decode().startswith("laitshow"):
            log.info(f"Connected to {address} (data: {data.decode()})")
            controller_ip = address[0]
            break

    r = requests.get(
        f"http://{controller_ip}:{configs["network"]["flask_port"]}/home/1"
    )
    log.info(r.status_code)
    log.info(r.json()["data"])

    coords = []
    with open(dir_path / "data.csv", "r") as coords_file:
        reader = csv.reader(coords_file)
        for row in reader:
            coords.append([int(d) for d in row])

    log.info("Lights in order")
    for coord in coords:
        requests.put(
            f'http://{controller_ip}:{configs["network"]["flask_port"]}/light/{coord[0]}',
            data={"color": "(255,255,255)"},
        )
        time.sleep(0.25)
        requests.put(
            f'http://{controller_ip}:{configs["network"]["flask_port"]}/light/{coord[0]}',
            data={"color": "(0,0,0)"},
        )
        time.sleep(0.25)

    log.info("Lights bottom to top")
    for coord in sorted(coords, itemgetter(2)):
        requests.put(
            f'http://{controller_ip}:{configs["network"]["flask_port"]}/light/{coord[0]}',
            data={"color": "(255,255,255)"},
        )
        time.sleep(0.25)
        requests.put(
            f'http://{controller_ip}:{configs["network"]["flask_port"]}/light/{coord[0]}',
            data={"color": "(0,0,0)"},
        )
        time.sleep(0.25)

    log.info("All lights out")
    requests.put(
        f'http://{controller_ip}:{configs["network"]["flask_port"]}/lights',
        data={"color": "(0,0,0)"},
    )


if __name__ == "__main__":
    main()
