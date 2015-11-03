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
    return struct.pack("!HH", OPCODE_DATA, blocknr) + data # TODO

def make_packet_ack(blocknr): # 
    return struct.pack("!HH", OPCODE_ACK, blocknr) # TODO

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
        blocknr = struct.unpack("!H", msg[2:4])
        data = msg[4:]
        return opcode, blocknr, data
    elif opcode == OPCODE_ACK:
        blocknr = struct.unpack("!H", msg[2:4])
        return opcode, blocknr
    elif opcode == OPCODE_ERR:
        errorcode = struct.unpack("!H", msg[2:4])
        errormsg = msg[4:].split('\0')
        return opcode, errorcode, errormsg
    else: 
        return ERROR_CODES[1]
    return None
    
def tftp_transfer(fd, hostname, direction, filename):
    # Implement this function
    # Open socket interface
    # Creating a socket to be used
    Port_ok = 6969

    server_addr = socket.getaddrinfo(hostname, Port_ok)[0][4:][0]
    server_addr_ip = server_addr[0]
    server_addr_port = server_addr[1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #socket.bind('', TFPT_PORT) # Leave to OS, fixes itself
        
    # Check if we are putting a file or getting a file and send
    #  the corresponding request.
    if direction == OPCODE_RRQ: #We want to Get file
        message = make_packet_rrq(filename, MODE_OCTET)
        sock.sendto(message, server_addr)
        last_recieved = 0

    elif direction == OPCODE_WRQ: #We want to Put file
        message = make_packet_wrq(filename, MODE_OCTET)
        sock.sendto(message, server_addr)
        i = 0;

    # Put or get the file, block by block, in a loop.
    while True:
        readable, writable, exceptional = select.select([sock], [], [], 1)
        if direction == TFTP_GET:
            if readable > 0: 
                chunk_of_data, addr = sock.recvfrom(516) # Recieve message from server
                opcode, blocknr, data = parse_packet(chunk_of_data) # Unpack message
                if len(data) >= 512 and last_recieved == blocknr[0]-1: # Not last chunk to be transfered and the package is the next in order
                    print "Created ack with nr " + str(blocknr[0])
                    ack = make_packet_ack(blocknr[0])
                    sock.sendto(ack, addr)
                    print "Sent ack to server"
                    print "Wrote to file"
                    fd.write(data)
                    last_recieved = blocknr[0]
                elif len(data) < 512 and last_recieved == blocknr[0]-1: # Last chunk to be transfered and the package is the next in order
                    print "Created ack with nr " + str(blocknr[0])
                    ack = make_packet_ack(blocknr[0])
                    sock.sendto(ack, addr)
                    print "Sent ack to server"
                    print "Wrote to file"
                    fd.write(data)
                    print "End of transfer"
                    break
                else:
                    ack = make_packet_ack(last_recieved) # Not the correct chunk sent, resend latest correct ack
                    sock.sendto(ack, addr)
                    print "Resent ack"
            else:
                print "Recieve timeout 5 sec"
                sock.Timeout(5)

            
        elif direction == TFTP_PUT:
            if readable > 0:
                chunk_of_data, addr = sock.recvfrom(516) # Recieve message from server
                opcode, blocknr, arg = parse_packet(chunk_of_data)
                if opcode == OPCODE_ACK and blocknr == i: # Check so it's the ack for the latest sent chunk
                    if len(fd[i*512:]) > 512:   # Check so we aren't in the end of file = last chunk
                        print "sending packet nr :" + str(i)
                        blocknr = i
                        chunk_to_be_sent = fd[i*512:(i+1)*512]
                        totalpacket = make_packet_data(blocknr, chunk_to_be_sent)
                        sock.sendto(totalpacket, server_addr)
                        i = i+1

                    else: # Last chunk to be sent, take the last data and make a chunk of it
                        blocknr = i
                        chunk_to_be_sent = fd[i*512:]
                        totalpacket = make_packet_data(blocknr, chunk_to_be_sent)
                        sock.sendto(totalpacket, server_addr)
                        print "Total file sent"
                        break
                else: 
                    print "Opcode: " + str(opcode) + " Errormsg: " + str(arg) # Error handling, returns error code and message
            else:
                print "Send timeout 5 sec" 
                sock.Timeout(5) # Time out for the socket if the message haven't been completly delivered

        else: 
            print "Failed miserably" #When all else fails!

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
