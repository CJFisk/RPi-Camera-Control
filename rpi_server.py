#!/usr/bin/env python
#Camera setup from https://projects.raspberrypi.org/en/projects/getting-started-with-picamera

#Code to control RPI pan and tilt servo from
#https://www.instructables.com/Raspberry-Pi-Cam-Pan-Tilt-Control-Over-Local-Inter/

#Code to transfer files using Sockets in Python based on code from
#https://www.thepythoncode.com/article/send-receive-files-using-sockets-python

#Imports
import socket
from socket import SHUT_RDWR
from picamera import PiCamera
from time import sleep
import datetime
from math import floor
import os
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

#Set up the RPi camera
camera = PiCamera()
camera.resolution = (1024, 768)
camera.rotation = 180     #Only if camera needs to be rotated
sleep(5)

#Set variables for labeling photos and videos
#If the folder is empty, the variable is set to 1
#Otherwise it is set to one more than the number of files currently in the folder
if len(os.listdir('images/')) > 0:
    photo_num = len(os.listdir('images/')) + 1
else:
    photo_num = 1

if len(os.listdir('videos/')) > 0:
    video_num = len(os.listdir('videos/')) + 1
else:
    video_num = 1
    
#Variable to keep track of whether a video is currently being recorded
video = False

#Set up pan and tilt servo
pan = 19     #GPIO 19
tilt = 6     #GPIO 6
GPIO.setup(pan, GPIO.OUT)
GPIO.setup(tilt, GPIO.OUT)

#Function to control pan/tilt servo
def setServoAngle(servo, angle):
    pwm = GPIO.PWM(servo, 50)
    pwm.start(8)
    dutyCycle = angle / 18. + 3.
    pwm.ChangeDutyCycle(dutyCycle)
    sleep(0.3)
    pwm.stop()

#Set up variables for TCP connection
TCP_PORT = 5006
BUFFER_SIZE = 1024
SEPARATOR = "<SEPARATOR>"

#Get IP Address - this can be replaced by using a constant for the IP address
#From https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM ) # UDP
sock.connect(('10.255.255.255', 1))
ip_addr = sock.getsockname()[0]
sock.detach()

#Open socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print('Socket Created')
sock.bind((ip_addr, TCP_PORT))
print('Bound to ', ip_addr, ':', TCP_PORT, sep='')

try:
    while True:
        print('Listening\n')
        sock.listen()

        conn, addr = sock.accept()
        print('Connection From ', addr[0], ':', addr[1], '\n', sep='')

        while True: #Keep receiving data until the connection is closed
            data = conn.recv(BUFFER_SIZE).decode('utf-8')
            if not data: break  #An empty packet signals the connection was closed

            print('Received Command:', data, '\n')
            
            command = data.split(' ')

            #If a video is in progress, only certain commands are accepted
            if video == True and command[0] not in ['END_VIDEO', 'PAN', 'TILT', 'STATUS_VIDEO']:
                conn.send(('ERROR: Video in progress').encode('utf-8'))
                continue
            
            #Return available commands
            if command[0] == 'QUERY':
                conn.send(('Available commands: ADJUST, COUNT, PAN, TILT, START_VIDEO, END_VIDEO, STATUS_VIDEO, PHOTO, SEND, QUIT').encode('utf-8'))
                
            #Adjust one of the settings of the RPi Camera
            elif command[0] == 'ADJUST':
                try:
                    setting = command[1]   #Setting to be changed
                    value = int(command[2])
                    
                    if setting == 'ROTATION':
                        if value in [0, 90, 180, 270]:
                            camera.rotation = value
                            conn.send(('ACK ROTATION %s' % command[2]).encode('utf-8'))
                        else:
                            conn.send(('Invalid value').encode('utf-8'))

                    else:
                        conn.send(('Unknown setting').encode('utf-8'))

                except:
                    conn.send(('Not enough arguments provided').encode('utf-8'))

            #Count the number of photos or vidoes currently stored
            elif command[0] == 'COUNT':
                try:
                    medium = command[1]
                    
                    if medium == 'PHOTO':
                        path = 'images/'
                        num = len(os.listdir(path))
                        conn.send(str(num).encode('utf-8'))
                    
                    elif medium == 'VIDEO':
                        path = 'videos/'
                        num = len(os.listdir(path))
                        conn.send(str(num).encode('utf-8'))
                    
                    else:
                        conn.send(('Unknown medium').encode('utf-8'))
                
                except:
                    conn.send(('Not enough arguments provided').encode('utf-8'))
            
            #Control the pan servo
            elif command[0] == 'PAN':
                try:
                    angle = int(command[1])
                    
                    if angle >=30 and angle <= 150:
                        setServoAngle(pan, angle)
                        conn.send(('ACK PAN %s' % (angle)).encode('utf-8'))
                    else:
                        conn.send(('Invalid angle').encode('utf-8'))

                except:
                    conn.send(('Not enough arguments provided').encode('utf-8'))
            
            #Control the tilt servo
            elif command[0] == 'TILT':
                try:
                    angle = int(command[1])
                    
                    if angle >=30 and angle <= 150:
                        setServoAngle(tilt, angle)
                        conn.send(('ACK TILT %s' % (angle)).encode('utf-8'))
                    else:
                        conn.send(('Invalid angle').encode('utf-8'))
                    
                except:
                    conn.send(('Not enough arguments provided').encode('utf-8'))
            
            #Start recording
            elif command[0] == 'START_VIDEO':
                video_start_time = datetime.datetime.now()
                camera.start_recording('videos/video%s.h264' % video_num)
                conn.send(('ACK START_VIDEO %s' % video_num).encode('utf-8'))
                video = True
                print('Recording started\n')

            #End recording
            elif command[0] == 'END_VIDEO':
                if video == True:
                    camera.stop_recording()
                    conn.send(('ACK END_VIDEO %s' % video_num).encode('utf-8'))
                    video_num += 1
                    video = False
                    print('Recording ended\n')
                else:
                    conn.send(('ERROR: No video to end').encode('utf-8'))

            #Find current length of video in minutes and seconds
            elif command[0] == 'STATUS_VIDEO':
                if video == True:
                    length = datetime.datetime.now() - video_start_time
                    length = length.total_seconds()
                    print(length, '\n')
                    conn.send(('Length: {} Minutes {} seconds'.format(floor(length/60), floor(length % 60))).encode('utf-8'))
                
                else:
                    conn.send(('Invalid command: no recording in progress').encode('utf-8'))
            
            #Take a photo
            elif command[0] == 'PHOTO':
                try:
                    num = int(command[1])         #Number of photos to take
                    interval = int(command[2])      #Interval between photos
                    
                    for i in range(num):
                        camera.capture('images/image%s.jpg' % photo_num)
                        photo_num += 1
                        sleep(interval)

                    conn.send(('ACK PHOTO %s' % (photo_num-1)).encode('utf-8'))
                
                except:
                    conn.send(('Not enough arguments provided').encode('utf-8'))
            
            #Send photo or video to the client
            #This command still needs troubleshooting
            elif command[0] == 'SEND':
                try:
                    medium = command[1]
                    value = int(command[2])
                    
                    if medium == 'PHOTO':
                        filename = 'images/image%s.jpg' % value
                        filesize = os.path.getsize(filename)
                        conn.send((f'{filename}<SEPARATOR>{filesize}').encode())
                        with open(filename, 'rb') as f:
                            while True:
                                bytes_read = f.read(BUFFER_SIZE)
                                if not bytes_read:
                                    break
                                conn.send(bytes_read)
                        break
                    
                    if medium == 'VIDEO':
                        filename = 'videos/video%s.h264' % value
                        filesize = os.path.getsize(filename)
                        conn.send((f'{filename}<SEPARATOR>{filesize}').encode())
                        with open(filename, 'rb') as f:
                            while True:
                                bytes_read = f.read(BUFFER_SIZE)
                                if not bytes_read:
                                    break
                                conn.send(bytes_read)
                                
                        break
                    
                except:
                    conn.send(('Not enough arguments provided').encode('utf-8'))
                    break
                
            #Close the socket
            elif command[0] == 'QUIT':
                break
            
            else:
                print('Unknown command\n')
                conn.send(('Unknown command').encode('utf-8'))
            
        conn.close()
        print('Connection Closed\n')
        
        if command[0] == 'QUIT':
            sock.shutdown(SHUT_RDWR)
            sock.close()
            camera.close()
            GPIO.cleanup()
            print("Server Stopped")
            break
        
except:
    sock.close()
    camera.close()
    GPIO.cleanup()
    print("Server Stopped")
