from ast import literal_eval
import board
import configparser
from flask import Flask, jsonify, request, url_for, redirect
import logger
import math
import neopixel
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time


log = logger.setup_logging()


class Controller:
    def __init__(self, configs):
        self.BOARD_PIN = getattr(board, configs["neopixels"]["board_pin"])
        self.NUM_PIXELS = int(configs["neopixels"]["count"])
        self.pixels = neopixel.NeoPixel(
            self.BOARD_PIN,
            self.NUM_PIXELS,
            brightness=0.2,
            auto_write=False,
            pixel_order=configs["neopixels"]["pixel_order"],
        )

        self.app = Flask(__name__)

        self.app.route("/home/<int:num>", methods=["GET"])(self.disp)
        self.app.route("/", methods=["GET", "POST"])(self.home)
        self.app.route("/version", methods=["GET", "PUT"])(self.update)
        self.app.route("/light/<int:ind>", methods=["PUT"])(self.light)
        self.app.route("/lights", methods=["PUT"])(self.lights)

        self._play_startup_animation()

    def disp(self, num):
        return jsonify({"data": num**2})

    def home(self):
        if request.method == "GET":
            data = "hello world"
            return jsonify({"data": data})
        elif request.method == "POST":
            # POST has to return a redirect
            return redirect(url_for("disp", num=19))

    def update(self):
        if request.method == "GET":
            return jsonify({"version": "TBD"})
        elif request.method == "PUT":
            if len(request.form["version"]):
                log.info("Updating...")
                dir_path = os.path.dirname(os.path.realpath(__file__))
                subprocess.run(["git", "-C", dir_path, "pull"])
                log.info("Update pulled. Restarting...")
                sys.exit()
            return jsonify({"version": "TBD"})

    def light(self, ind):
        if request.method == "PUT":
            log.info(f"light {ind} {request.form['color']}")
            self.pixels[ind] = literal_eval(request.form["color"])
            if "brightness" in request.form:
                self.pixels.brightness = request.form["brightness"]
            self.pixels.show()
            return jsonify({"success": f"{ind}"})

    def lights(self):
        if request.method == "PUT":
            self.pixels.fill(literal_eval(request.form["color"]))
            if "brightness" in request.form:
                self.pixels.brightness = request.form["brightness"]
            self.pixels.show()
            return jsonify({"success": f"1"})

    def _play_startup_animation(self):
        self.pixels.fill((255, 255, 255))
        self.pixels.brightness = 1.0
        self.pixels.show()

        DURATION = 5
        start = time.time()
        while (curr := time.time() - start) < DURATION:
            percent_complete = curr / DURATION
            curr_frac = math.ceil(math.log2(1 - percent_complete))
            next_frac = math.floor(math.log2(1 - percent_complete))
            if curr_frac == next_frac:
                self.pixels.brightness = 0
                self.pixels.show()
                continue
            percent_curr_frac = percent_complete - (1 - 2**curr_frac)
            brightness = 1 - math.sqrt(percent_curr_frac / 2**next_frac)
            self.pixels.brightness = brightness
            self.pixels.show()
            # let lights finish changing brightness before next cycle
            time.sleep(0.01)

        self.pixels.brightness = 0
        self.pixels.show()

    def run(self):
        self.app.run(host="0.0.0.0")


def advertise_server(mcast_grp, mcast_port):
    log.info("Starting multicast controller advertising")
    MULTICAST_TTL = 2
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
    while True:
        sock.sendto("laitshow".encode(), (mcast_grp, mcast_port))
        time.sleep(5)


def main():
    dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
    configs = configparser.ConfigParser()
    configs.read(dir_path / "settings.ini")

    threading.Thread(
        target=advertise_server,
        args=(configs["network"]["mcast_grp"], int(configs["network"]["mcast_port"])),
        daemon=True,
    ).start()

    controller = Controller(configs)
    controller.run()


if __name__ == "__main__":
    main()
