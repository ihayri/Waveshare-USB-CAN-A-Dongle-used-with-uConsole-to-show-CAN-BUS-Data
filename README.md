# Waveshare-USB-CAN-A-Dongle-used-with-uConsole-to-show-CAN-BUS-Data
CAN Gauge – OBD2 Live Data Reader A real-time vehicle dashboard that reads OBD2 data over CAN bus using a Waveshare USB-CAN adapter. Built with Python, this tool displays live engine parameters in a clean, collision-proof terminal UI.

https://www.waveshare.com/usb-can-a.htm?srsltid=AfmBOooYW8yivWAwoNYXT7TwFn4_5JUhXqPOBoc9Ek3DjfvuyQxJAsAt

<img width="3628" height="2041" alt="IMG_20260613_091141492_HDR" src="https://github.com/user-attachments/assets/09e556fb-116e-4425-81ea-bee42f1e636d" />

https://youtu.be/1icTISAF99w


✅ HOW WE MADE THE CAN GAUGE WORK (TEXT HOW‑TO)
1
Identify the Correct USB Port
Start Here
The Waveshare USB‑CAN adapter kept changing from ttyUSB2 to ttyUSB0.

Run ls -la /dev/ttyUSB* to see which port exists

Adapter appeared as /dev/ttyUSB0 instead of USB2

Update the Python script: PORT = "/dev/ttyUSB0"

2
Verify Serial Communication
The adapter requires a stable serial connection before CAN frames can be exchanged.

Confirm pyserial is installed: python3 -c "import serial"

Use baudrate 2000000 (or fallback to 1000000 if unstable)

Add a 0.5s delay after opening the serial port

3
Start the CAN Receiver Thread
The script must continuously read incoming frames from the adapter.

Call start_rx() after connecting

The RX loop collects frames into _responses

Ensures OBD2 replies are captured asynchronously

4
Send Proper OBD2 Request Frames
The ECU only responds to correctly formatted CAN frames.

Use CAN ID 0x7DF for broadcast requests

Use data format [0x02, 0x01, PID, 0x00 ...]

ECU replies on 0x7E8

5
Parse Waveshare USB‑CAN Frames
The adapter wraps CAN frames in its own protocol.

Frame format: 0xAA | 0xC0 | ID_L | ID_H | DATA... | 0x55

Extract CAN ID and data length

Store responses in _responses[0x7E8]

6
Read PIDs and Convert Values
Each PID requires a formula to convert raw bytes into human-readable values.

RPM: (A*256 + B) / 4

Speed: A

Coolant Temp: A - 40

Throttle: (A * 100) / 255

Store formulas in the PIDS list

7
Build a Wide, Collision‑Proof Curses UI
The display must avoid overlapping values and units.

Use two wide columns

Place values at x + 22

Place units at x + 34 to prevent overwriting

Add timestamp, title, and footer

Refresh at ~20 FPS

8
Launch in Fullscreen Xterm
Fullscreen ensures consistent layout and spacing.

Create launcher script using xterm: xterm -fullscreen -fa 'Monospace' -fs 16 -e "python3 /home/dragon/obd2_reader.py"

Add executable permission: chmod +x

9
Verify Live Data
Once running, the gauge should show stable real‑time values.

Speed updates instantly

RPM responds smoothly

Coolant and throttle show correct ranges

No more unit overwriting (km/h stays intact)
