#!/usr/bin/env python3

#Imports
import socket
import tqdm
import os

#Enter IP address of server
TCP_IP = '10.62.6.148'
TCP_PORT = 5006
BUFFER_SIZE = 1024
SEPARATOR = '<SEPARATOR>'

#Create socket and connect to server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("Socket Created", s)
s.connect((TCP_IP,TCP_PORT))
print("Connected\n")

#Keep connection open indefinitely
try:
    while True:
        
        #Enter message
        MESSAGE = input('Command: ')
        s.send(MESSAGE.encode('utf-8'))

        #Close the connection
        if MESSAGE == 'QUIT':
            s.close()
            print("Closed")
            break
            
        else:
            print("Command Sent\n")
            
            #Receive photo/video data
            #This will also close the connection
            if MESSAGE.split(' ')[0] == 'SEND':
                received = s.recv(BUFFER_SIZE).decode()
                filename, filesize = received.split(SEPARATOR)
                filesize = int(filesize)
                progress = tqdm.tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True, unit_divisor=1024)
                with open(filename, 'wb') as f:
                    while True:
                        bytes_read = s.recv(BUFFER_SIZE)
                        if not bytes_read:
                            break
                        f.write(bytes_read)
                        progress.update(len(bytes_read))
                    break
            
            #Receive any other kind of data
            else:
                data = s.recv(BUFFER_SIZE).decode('utf-8')
                print("Received Data: ", data, "\n")

except:
    s.close()
    print("Closed")
