from ast import literal_eval
import board
import configparser
from flask import Flask, jsonify, request, url_for, redirect
import logger
import neopixel
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time


app = Flask(__name__)
log = logger.setup_logging()
BOARD_PIN = None
NUM_PIXELS = None
pixels = None


# on the terminal type: curl http://127.0.0.1:5000/
# returns hello world when we use GET.
# returns the data that we send when we use POST.
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        data = "hello world"
        return jsonify({"data": data})
    elif request.method == "POST":
        # POST has to return a redirect
        return redirect(url_for("disp", num=19))


# A simple function to calculate the square of a number
# the number to be squared is sent in the URL when we use GET
# on the terminal type: curl http://127.0.0.1:5000 / home / 10
# this returns 100 (square of 10)
@app.route("/home/<int:num>", methods=["GET"])
def disp(num):
    return jsonify({"data": num**2})


@app.route("/version", methods=["GET", "PUT"])
def update():
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


@app.route("/light/<int:ind>", methods=["PUT"])
def light(ind):
    if request.method == "PUT":
        log.info(f"light {ind} {request.form['color']}")
        pixels[ind] = literal_eval(request.form["color"])
        pixels.show()
        return jsonify({"success": f"{ind}"})


@app.route("/lights", methods=["PUT"])
def lights():
    if request.method == "PUT":
        pixels.fill(literal_eval(request.form["color"]))
        pixels.show()
        return jsonify({"success": f"1"})


def advertise_server(mcast_grp, mcast_port):
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

    log.info("Starting multicast controller advertising")
    threading.Thread(
        target=advertise_server,
        args=(configs["network"]["mcast_grp"], int(configs["network"]["mcast_port"])),
        daemon=True,
    ).start()

    global BOARD_PIN
    global NUM_PIXELS
    global pixels
    BOARD_PIN = board.D21  # TODO: make this settable via configs
    NUM_PIXELS = int(configs["neopixels"]["count"])
    pixels = neopixel.NeoPixel(
        BOARD_PIN,
        NUM_PIXELS,
        brightness=0.2,
        auto_write=False,
        pixel_order=configs["neopixels"]["pixel_order"],
    )

    app.run(host="0.0.0.0")


if __name__ == "__main__":
    main()
