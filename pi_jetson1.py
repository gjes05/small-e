# p_controller_pi_final_inverted_y.py
import socket
import time
import pigpio


# --- Constants ---
HOST_IP = '0.0.0.0'
PORT = 5000


# Pin assignments
PAN_PIN = 17
TILT_PIN = 18


# ANGLE LIMITS
PAN_MIN_ANGLE = 0
PAN_MAX_ANGLE = 180
TILT_MIN_ANGLE = 90
TILT_MAX_ANGLE = 180


# Define the "home" or "center" positions
PAN_HOME = 90.0
TILT_HOME = 180.0


# Servo pulse width calibration
SERVO_MIN_PULSE = 500
SERVO_MAX_PULSE = 2500


# P-Controller Gain (Tune these values for smooth operation)
Kp_pan = 0.1
Kp_tilt = 0.2


def map_angle_to_pulse(angle):
   return SERVO_MIN_PULSE + (angle / 180.0) * (SERVO_MAX_PULSE - SERVO_MIN_PULSE)


pi = None
try:
   # --- Setup ---
   pi = pigpio.pi()
   if not pi.connected:
       print("Error: Could not connect to pigpio daemon.")
       exit()


   pi.set_servo_pulsewidth(PAN_PIN, map_angle_to_pulse(PAN_HOME))
   pi.set_servo_pulsewidth(TILT_PIN, map_angle_to_pulse(TILT_HOME))
   time.sleep(1)


   target_pan_angle = PAN_HOME
   target_tilt_angle = TILT_HOME


   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   sock.bind((HOST_IP, PORT))


   print(f"--- Raspberry Pi Absolute P-Controller Initialized ---")
   print("Ready to receive coordinate data or 'NA' for lost target.")
   print(f"Pan Home: {PAN_HOME} (GPIO 17), Tilt Home: {TILT_HOME} (GPIO 18)")
   print("Waiting for first packet from Xavier...")
   print("----------------------------------------------------------------")


   first_packet_received = False


   while True:
       data, addr = sock.recvfrom(1024)
      
       if not first_packet_received:
           print(f"\n--- Connection Established! Packet received from: {addr} ---\n")
           first_packet_received = True


       try:
           message = data.decode('utf-8')
           coords = message.split(',')


           if coords[0] == 'NA':
               print("[PI] Target lost. Holding last position.", end='\r')
               continue
          
           error_x = int(coords[0])
           error_y = int(coords[1])
          
           # --- Pan Control Logic ---
           target_pan_angle = PAN_HOME - (Kp_pan * error_x)


           # ### MODIFIED: Final Tilt Control Logic as per your request ###
           # Only calculate a new target angle if the face is ABOVE center (positive error_y).
           if error_y > 0:
               # error_y is positive, so we can use it directly in the calculation.
               correction = Kp_tilt * error_y
               # Subtract the correction to move the angle from 180 down towards 90.
               target_tilt_angle = TILT_HOME - correction
           # If error_y is negative, the target_tilt_angle remains unchanged, holding its position.
          
           # Clamp the final target angles
           clamped_pan_angle = max(PAN_MIN_ANGLE, min(PAN_MAX_ANGLE, target_pan_angle))
           clamped_tilt_angle = max(TILT_MIN_ANGLE, min(TILT_MAX_ANGLE, target_tilt_angle))


           # Convert to integer pulse widths
           pan_pulse = int(map_angle_to_pulse(clamped_pan_angle))
           tilt_pulse = int(map_angle_to_pulse(clamped_tilt_angle))


           # Command the Servos
           pi.set_servo_pulsewidth(PAN_PIN, pan_pulse)
           pi.set_servo_pulsewidth(TILT_PIN, tilt_pulse)


           print(f"Error(x,y): ({error_x:4d}, {error_y:4d}) -> Target Angle(p,t): ({clamped_pan_angle:6.1f}, {clamped_tilt_angle:6.1f})")
          
       except (ValueError, IndexError):
           print(f"[PI] WARNING: Received malformed data: {data}")
           continue


except KeyboardInterrupt:
   print("\nCtrl+C detected. Shutting down.")


finally:
   if pi and pi.connected:
       print("Returning servos to home and stopping PWM.")
       pi.set_servo_pulsewidth(PAN_PIN, map_angle_to_pulse(PAN_HOME))
       pi.set_servo_pulsewidth(TILT_PIN, map_angle_to_pulse(TILT_HOME))
       time.sleep(1)
       pi.set_servo_pulsewidth(PAN_PIN, 0)
       pi.set_servo_pulsewidth(TILT_PIN, 0)
       pi.stop()







