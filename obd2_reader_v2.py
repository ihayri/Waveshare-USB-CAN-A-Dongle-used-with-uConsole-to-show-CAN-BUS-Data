#!/usr/bin/env python3
import sys
import time
import curses
import serial
import threading

PORT = "/dev/ttyUSB0"
SERIAL_BAUD = 2000000
OBD2_REQUEST_ID = 0x7DF
OBD2_RESPONSE_ID = 0x7E8

PIDS = [
    (0x0C, "RPM",            lambda d: f"{round((d[0]*256 + d[1]) / 4):.0f}", "rpm"),
    (0x0D, "Speed",          lambda d: f"{d[0]}", "km/h"),
    (0x05, "Coolant Temp",   lambda d: f"{d[0] - 40}", "C"),
    (0x0F, "Intake Temp",    lambda d: f"{d[0] - 40}", "C"),
    (0x04, "Engine Load",    lambda d: f"{round(d[0] * 100 / 255, 1)}", "%"),
    (0x11, "Throttle",       lambda d: f"{round(d[0] * 100 / 255, 1)}", "%"),
    (0x2F, "Fuel Level",     lambda d: f"{round(d[0] * 100 / 255, 1)}", "%"),

    # NEW 7 PIDs
    (0x42, "Battery Volt",   lambda d: f"{round((d[0]*256 + d[1]) / 1000, 2)}", "V"),
    (0x46, "Ambient Temp",   lambda d: f"{d[0] - 40}", "C"),
    (0x45, "Throttle Pos2",  lambda d: f"{round(d[0] * 100 / 255, 1)}", "%"),
    (0x5C, "Oil Temp",       lambda d: f"{d[0] - 40}", "C"),
    (0x3C, "Cat Temp B1",    lambda d: f"{round((d[0]*256 + d[1]) / 10, 1)}", "C"),
    (0x3D, "Cat Temp B2",    lambda d: f"{round((d[0]*256 + d[1]) / 10, 1)}", "C"),
    (0x0B, "MAP Sensor",     lambda d: f"{d[0]}", "kPa"),
]

class WaveshareCAN:
    def __init__(self, port):
        self.port = port
        self.ser = None
        self._responses = {}
        self._running = False

    def connect(self):
        self.ser = serial.Serial(self.port, baudrate=SERIAL_BAUD, timeout=0.5)
        time.sleep(0.5)
        return True

    def _build_frame(self, can_id, data):
        frame = bytearray()
        frame.append(0xAA)
        frame.append(0xC0 | (len(data) & 0x0F))
        frame.append(can_id & 0xFF)
        frame.append((can_id >> 8) & 0xFF)
        frame.extend(data)
        frame.append(0x55)
        return bytes(frame)

    def _parse_frame(self, buf):
        try:
            if len(buf) < 7:
                return None, 0
            if buf[0] != 0xAA:
                return None, 1
            type_byte = buf[1]
            data_len = type_byte & 0x0F
            if len(buf) < 4 + data_len + 1:
                return None, 0
            can_id = buf[2] | (buf[3] << 8)
            data = list(buf[4:4+data_len])
            if buf[4+data_len] == 0x55:
                return (can_id, data), (4 + data_len + 1)
            return None, 1
        except:
            return None, 1

    def send_frame(self, can_id, data):
        frame = self._build_frame(can_id, data)
        self.ser.write(frame)

    def start_rx(self):
        self._running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()

    def _rx_loop(self):
        buf = bytearray()
        while self._running:
            try:
                if self.ser.in_waiting:
                    buf.extend(self.ser.read(self.ser.in_waiting))
                    while len(buf) >= 7:
                        result, consumed = self._parse_frame(buf)
                        if result:
                            can_id, data = result
                            self._responses[can_id] = data
                            buf = buf[consumed:]
                        elif consumed > 0:
                            buf = buf[consumed:]
                        else:
                            break
                else:
                    time.sleep(0.001)
            except:
                pass

    def read_obd2_pid(self, pid, timeout=0.1):
        self._responses.pop(OBD2_RESPONSE_ID, None)
        data = [0x02, 0x01, pid, 0, 0, 0, 0, 0]
        self.send_frame(OBD2_REQUEST_ID, data)
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self._responses.get(OBD2_RESPONSE_ID)
            if resp and len(resp) >= 3 and resp[1] == 0x41 and resp[2] == pid:
                return resp[3:]
            time.sleep(0.01)
        return None

    def close(self):
        self._running = False
        if self.ser:
            self.ser.close()

def run_display(stdscr, can):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)

    stdscr.clear()
    h, w = stdscr.getmaxyx()

    title = "  2007 Chrysler 300C — OBD2 Live Data (Version 2)  "
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addstr(0, 0, "═" * w)
    stdscr.addstr(1, (w - len(title)) // 2, title)
    stdscr.addstr(2, 0, "═" * w)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)

    col1_x = 4
    col2_x = w // 2 + 4
    value_offset = 22
    unit_offset  = 34

    half = len(PIDS) // 2

    for i, (pid, name, formula, unit) in enumerate(PIDS):
        if i < half:
            x = col1_x
            y = 5 + i * 3
        else:
            x = col2_x
            y = 5 + (i - half) * 3

        stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        stdscr.addstr(y, x, f"{name:<18}")
        stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)

        stdscr.attron(curses.color_pair(5))
        stdscr.addstr(y, x + unit_offset, unit)
        stdscr.attroff(curses.color_pair(5))

    footer = " Press Q to quit "
    stdscr.attron(curses.color_pair(1))
    stdscr.addstr(h - 2, 0, "═" * w)
    stdscr.addstr(h - 1, (w - len(footer)) // 2, footer)
    stdscr.attroff(curses.color_pair(1))

    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key in (ord('q'), ord('Q')):
            break

        stdscr.attron(curses.color_pair(1))
        stdscr.addstr(1, 4, f"Last Update: {time.strftime('%H:%M:%S')}")
        stdscr.attroff(curses.color_pair(1))

        for i, (pid, name, formula, unit) in enumerate(PIDS):
            if i < half:
                x = col1_x
                y = 5 + i * 3
            else:
                x = col2_x
                y = 5 + (i - half) * 3

            value_x = x + value_offset
            stdscr.addstr(y, value_x, " " * 10)

            data = can.read_obd2_pid(pid)

            if data:
                try:
                    value = formula(data)
                    stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
                    stdscr.addstr(y, value_x, f"{value:>8}")
                    stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
                except:
                    stdscr.attron(curses.color_pair(4))
                    stdscr.addstr(y, value_x, " ERR")
                    stdscr.attroff(curses.color_pair(4))
            else:
                stdscr.attron(curses.color_pair(4))
                stdscr.addstr(y, value_x, " N/A")
                stdscr.attroff(curses.color_pair(4))

        stdscr.refresh()
        time.sleep(0.05)

def main():
    can = WaveshareCAN(PORT)
    try:
        can.connect()
        can.start_rx()
        time.sleep(0.5)
        curses.wrapper(run_display, can)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)
    finally:
        can.close()

if __name__ == "__main__":
    main()