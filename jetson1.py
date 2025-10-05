# sender_xavier_face_udp.py
import pyrealsense2 as rs
import numpy as np
import cv2
from deepface import DeepFace
import socket
import time

# ============================
# UDP Setup
# ============================
SERVER_IP = "192.168.10.2"  # Pi's IP
SERVER_PORT = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = (SERVER_IP, SERVER_PORT)

# ============================
# Configuration
# ============================
CONFIDENCE_THRESHOLD = 0.80
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CENTER_X = FRAME_WIDTH // 2
CENTER_Y = FRAME_HEIGHT // 2

print(f"--- Xavier UDP Sender Initialized ---")
print(f"Streaming face coordinates to Pi at {server_address}")
print("Press 'q' to quit.")
print("-------------------------------------")

# ============================
# RealSense Setup
# ============================
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, FRAME_WIDTH, FRAME_HEIGHT, rs.format.bgr8, 30)
pipeline.start(config)

try:
    while True:
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue
        frame = np.asanyarray(color_frame.get_data())

        # Detect faces
        try:
            faces = DeepFace.extract_faces(frame, detector_backend='opencv', enforce_detection=False)
        except Exception:
            faces = []

        if faces and faces[0]['confidence'] > CONFIDENCE_THRESHOLD:
            face = faces[0]
            x, y, w, h = face['facial_area'].values()
            face_center_x = x + w // 2
            face_center_y = y + h // 2

            # Normalized coordinates: [-1,1]
            norm_x = (face_center_x - CENTER_X) / (FRAME_WIDTH / 2)
            norm_y = (CENTER_Y - face_center_y) / (FRAME_HEIGHT / 2)  # positive = up
            message = f"{norm_x:.3f},{norm_y:.3f}".encode('utf-8')

            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"Conf: {face['confidence']:.2f}", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            print(f"Sent: ({norm_x:.2f},{norm_y:.2f}) | Conf: {face['confidence']:.2f}")

        else:
            message = "NA,NA".encode('utf-8')
            print("No face detected. Sending NA,NA", end='\r')

        # Send UDP message
        try:
            sock.sendto(message, server_address)
        except Exception as e:
            print(f"Error sending: {e}")

        # Display
        cv2.imshow("Face Detection", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()
    sock.close()
    print("Sender shutdown.")

# server_pi_pd_controller.py
import socket
import time
import pigpio

# ============================
# Servo & UDP Setup
# ============================
HOST_IP = "0.0.0.0"
PORT = 5000

PAN_PIN = 17
TILT_PIN = 18

PAN_HOME = 90
TILT_HOME = 90
PAN_MIN = 0
PAN_MAX = 180
TILT_MIN = 0
TILT_MAX = 180
SERVO_MIN_PULSE = 500
SERVO_MAX_PULSE = 2500

# PD Gains
Kp_pan = 35    # scaled for normalized input [-1,1]
Kd_pan = 15
Kp_tilt = 35
Kd_tilt = 15

def map_angle_to_pulse(angle):
    return SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)

# ============================
# Initialize
# ============================
pi = pigpio.pi()
if not pi.connected:
    exit("Error: pigpio daemon not running. Run sudo pigpiod")

# Center servos
pi.set_servo_pulsewidth(PAN_PIN, map_angle_to_pulse(PAN_HOME))
pi.set_servo_pulsewidth(TILT_PIN, map_angle_to_pulse(TILT_HOME))
time.sleep(1)

# UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST_IP, PORT))
sock.setblocking(False)

print("--- Pi PD Controller Running ---")

# PD state variables
last_error_x = 0
last_error_y = 0
last_time = time.time()
current_pan = PAN_HOME
current_tilt = TILT_HOME

try:
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            message = data.decode('utf-8')
            if message.startswith("NA"):
                print("No target. Holding position.", end='\r')
                continue
            error_x_str, error_y_str = message.split(",")
            error_x = float(error_x_str)
            error_y = float(error_y_str)

            # PD Calculation
            now = time.time()
            dt = max(0.01, now - last_time)

            # Pan
            p_pan = Kp_pan * error_x
            d_pan = Kd_pan * ((error_x - last_error_x) / dt)
            current_pan = PAN_HOME - (p_pan + d_pan)

            # Tilt
            p_tilt = Kp_tilt * error_y
            d_tilt = Kd_tilt * ((error_y - last_error_y) / dt)
            current_tilt = TILT_HOME - (p_tilt + d_tilt)

            # Clamp
            current_pan = max(PAN_MIN, min(PAN_MAX, current_pan))
            current_tilt = max(TILT_MIN, min(TILT_MAX, current_tilt))

            # Command servos
            pi.set_servo_pulsewidth(PAN_PIN, map_angle_to_pulse(current_pan))
            pi.set_servo_pulsewidth(TILT_PIN, map_angle_to_pulse(current_tilt))

            # Update PD state
            last_error_x = error_x
            last_error_y = error_y
            last_time = now

            print(f"Errors(x,y): ({error_x:.2f},{error_y:.2f}) -> Pan,Tilt: ({current_pan:.1f},{current_tilt:.1f})", end='\r')

        except BlockingIOError:
            # No data received, continue loop
            time.sleep(0.01)
        except Exception as e:
            print(f"Error: {e}")
            continue

except KeyboardInterrupt:
    print("\nStopping...")

finally:
    # Return to home
    pi.set_servo_pulsewidth(PAN_PIN, map_angle_to_pulse(PAN_HOME))
    pi.set_servo_pulsewidth(TILT_PIN, map_angle_to_pulse(TILT_HOME))
    time.sleep(1)
    pi.set_servo_pulsewidth(PAN_PIN, 0)
    pi.set_servo_pulsewidth(TILT_PIN, 0)
    pi.stop()
    sock.close()
    print("Server shutdown.")


