import configparser
import csv
import cv2
import os
from pathlib import Path

import logger


log = logger.setup_logging()


def map_lights():
    mapper = Mapper()
    mapper.run()


class Mapper:
    def __init__(self):
        dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
        self.configs = configparser.ConfigParser()
        self.configs.read(dir_path / "../settings.ini")

        self.webcam = Webcam()

    def _take_mapping_images(self, rotation: int):
        # set all lights off
        for i in range(self.configs["neopixels"]["count"]):
            # take image of off
            # set light on
            # take image of on
            # set light off
            pass

    def _process_mapping_images(self, rotation: int):
        locs = []
        for i in range(self.configs["neopixels"]["count"]):
            on = cv2.imread(f"calibration/{i:02}_on.jpg")
            off = cv2.imread(f"calibration/{i:02}_off.jpg")
            sub = cv2.subtract(on, off)
            blur = cv2.GaussianBlur(sub, (91, 91), 0)
            (_, _, _, maxLoc) = cv2.minMaxLoc(cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY))
            print(f"{i}: {maxLoc}")
            locs.append((i, maxLoc[0], maxLoc[1]))

        left = locs[0][1]
        right = locs[0][1]
        top = locs[0][2]
        bottom = locs[0][2]

        for i in range(len(locs)):
            if locs[i][1] < left:
                left = locs[i][1]
            if locs[i][1] > right:
                right = locs[i][1]
            if locs[i][2] < top:
                top = locs[i][2]
            if locs[i][2] > bottom:
                bottom = locs[i][2]

        print(f"{bottom} {left} {top} {right}")

        cv2.rectangle(sub, (left, bottom), (right, top), (0, 0, 255), 2)
        cv2.imshow("bounds", sub)
        cv2.waitKey(2000)

        with open("data.csv", "w") as file:
            writer = csv.writer(file)
            writer.writerows(locs)

    def _calc_coords(self):
        # do coord math here
        pass

    def _debug(self):
        # out = sub.copy()
        # (minVal, maxVal, minLoc, maxLoc) = cv2.minMaxLoc(red[:, :, 2])
        # cv2.circle(out, maxLoc, 11, (255, 0, 0), 2)
        # cv2.imshow(f"{i}", out)
        # cv2.waitKey(750)
        # input()
        # cv2.destroyAllWindows()
        pass

    def run(self):
        for r in [0, 90, 180, 270]:
            self._take_mapping_images(r)
            self._process_mapping_images(r)
        self._calc_coords()


class Webcam:
    def __init__(self):
        dir_path = Path(os.path.dirname(os.path.realpath(__file__)))
        self.configs = configparser.ConfigParser()
        self.configs.read(dir_path / "../settings.ini")

        # Get a handle for the webcam
        self.cap = cv2.VideoCapture(int(self.configs["webcam"]["index"]))

        if not self.cap.isOpened():
            log.error("Could not open the webcam")
            exit()

    # TODO: What is the proper name of this method?
    def __exit__(self):
        self.cap.release()
        cv2.destroyAllWindows()

    def grab_frame(self):
        for _ in range(4):
            self.cap.read()
        ret, frame = self.cap.read()

        if ret:
            print(f"Photo 2 saved successfully")
            return frame
        log.error("Failed to capture a frame")

    def save_frame(self):
        frame = self.grab_frame()
        cv2.imwrite(f"img_name.jpg", frame)
