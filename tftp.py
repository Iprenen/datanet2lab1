#! /usr/bin/python

import sys,socket,struct,select

BLOCK_SIZE= 512

OPCODE_RRQ=   1
OPCODE_WRQ=   2
OPCODE_DATA=  3
OPCODE_ACK=   4
OPCODE_ERR=   5

MODE_NETASCII= "netascii" 
MODE_OCTET=    "octet" # Use this!
MODE_MAIL=     "mail"

TFTP_PORT= 69

# Timeout in seconds
TFTP_TIMEOUT= 2

ERROR_CODES = ["Undef",
               "File not found",
               "Access violation",
               "Disk full or allocation exceeded",
               "Illegal TFTP operation",
               "Unknown transfer ID",
               "File already exists",
               "No such user"]

# Internal defines
TFTP_GET = 1
TFTP_PUT = 2


def make_packet_rrq(filename, mode):
    # Note the exclamation mark in the format string to pack(). What is it for? OPcode = 0
    return struct.pack("!H", OPCODE_RRQ) + filename + '\0' + mode + '\0'

def make_packet_wrq(filename, mode):
    return struct.pack("!H", OPCODE_WRQ) + filename + '\0' + mode + '\0' 
    # TODO Write code for send wrq request, check if  ACK = Blocknr 0 => accepted, OPcode = 1

def make_packet_data(blocknr, data): #Opcode = 3
    return struct.pack("!HH", OPCODE_DATA) + blocknr + data # TODO

def make_packet_ack(blocknr): # 
    return struct.pack("!HH", OPCODE_ACK) + blocknr # TODO

def make_packet_err(errcode, errmsg):
    return struct.pack("!H", OPCODE_ERR) + errcode + errmsg + '\0' # TODO

def parse_packet(msg):
    """This function parses a recieved packet and returns a tuple where the
        first value is the opcode as an integer and the following values are
        the other parameters of the packets in python data types"""
    opcode = struct.unpack("!H", msg[:2])[0]
    if opcode == OPCODE_RRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    elif opcode == OPCODE_WRQ:
        l = msg[2:].split('\0')
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    elif opcode == OPCODE_DATA:
        blocknr = msg[2:3]
        data = msg[4:]
        if len(data) < 512:
            last = 1
        else: 
            last = 0
        return opcode, blocknr, data, last
    elif opcode == OPCODE_ACK:
        blocknr = msg[2:]
        return opcode, blocknr
    elif opcode == OPCODE_ERR:
        errorcode = msg[2:3]
        errormsg = msg[4:].split('\0')
        return opcode, errorcode, errormsg
    else: 
        return ERROR_CODES[1]
    return None
    
def tftp_transfer(fd, hostname, direction, filename):
    # Implement this function
    
    # Open socket interface
    # Creating a socket to be used
    socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #socket.bind('', TFPT_PORT) # Leave to OS, fixes itself
        
    # Check if we are putting a file or getting a file and send
    #  the corresponding request.
    if direction == OPCODE_RRQ: #We want to Get file
        message = make_packet_rrq(filename, MODE_OCTET)
        socket.sendto(message, hostname)
        f = open('received_file', 'wb')

    elif direction == OPCODE_WRQ: #We want to Put file
        message = make_packet_wrq(filename, MODE_OCTET)
        socket.sendto(message, hostname)
        msg = socket.recv(516) # message from server
        answer = parse_package(msg)
    # Put or get the file, block by block, in a loop.
    while True:
        msg = socket.recv(516) # Recieve message from server
        answer = parse_package(msg)
        if answer[0] == 3:
            blocknr = answer[1]
            data = answer[2]
            socket.sendto(make_packet_ack(blocknr), hostname)
            f.write(data)
            
        elif answer[0] == 4:
            tot_sent = 0
            tot_packet = len(filename)
            while tot_sent < tot_packet:
                sent = socket.send(filename) #May or may not be right parameter here...
                tot_sent.append(sent)

        # Wait for packet, write the data to the filedescriptor or
        # read the next block from the file. Send new packet to server.
        # Don't forget to deal with timeouts and received error packets.
        # r,w,e = socket.select
        pass


def usage():
    """Print the usage on stderr and quit with error code"""
    sys.stderr.write("Usage: %s [-g|-p] FILE HOST\n" % sys.argv[0])
    sys.exit(1)


def main():
    # No need to change this function
    direction = TFTP_GET
    if len(sys.argv) == 3:
        filename = sys.argv[1]
        hostname = sys.argv[2]
    elif len(sys.argv) == 4:
        if sys.argv[1] == "-g":
            direction = TFTP_GET
        elif sys.argv[1] == "-p":
            direction = TFTP_PUT
        else:
            usage()
            return
        filename = sys.argv[2]
        hostname = sys.argv[3]
    else:
        usage()
        return

    if direction == TFTP_GET:
        print "Transfer file %s from host %s" % (filename, hostname)
    else:
        print "Transfer file %s to host %s" % (filename, hostname)

    try:
        if direction == TFTP_GET:
            fd = open(filename, "wb")
        else:
            fd = open(filename, "rb")
    except IOError as e:
        sys.stderr.write("File error (%s): %s\n" % (filename, e.strerror))
        sys.exit(2)

    tftp_transfer(fd, hostname, direction, filename)
    fd.close()

if __name__ == "__main__":
    main()
