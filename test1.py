#!/usr/bin/env python

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

# Timeout in seconds
TFTP_TIMEOUT= 0.1

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


def make_packet_rrq(filename, mode): #Opcode = 1
    return struct.pack("!H", OPCODE_RRQ) + filename + '\0' + mode + '\0'

def make_packet_wrq(filename, mode): #Opcode = 2
    return struct.pack("!H", OPCODE_WRQ) + filename + '\0' + mode + '\0'

def make_packet_data(blocknr, data): #Opcode = 3
    return struct.pack("!HH", OPCODE_DATA, blocknr) + data 

def make_packet_ack(blocknr): #Opcode = 4
    return struct.pack("!HH", OPCODE_ACK, blocknr) 

def make_packet_err(errcode, errmsg): #Opcode = 5
    return struct.pack("!H", OPCODE_ERR) + errcode + errmsg + '\0' 

def parse_packet(msg):
    """This function parses a recieved packet and returns a tuple where the
        first value is the opcode as an integer and the following values are
        the other parameters of the packets in python data types"""
    opcode = struct.unpack("!H", msg[:2])[0]
    if opcode == OPCODE_RRQ:
        l = msg[2:].split('\0') # Extract arguments
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    elif opcode == OPCODE_WRQ:
        l = msg[2:].split('\0') #Extract arguments
        if len(l) != 3:
            return None
        return opcode, l[1], l[2]
    elif opcode == OPCODE_DATA:
        blocknr = struct.unpack("!H", msg[2:4]) # Get blocknr
        data = msg[4:]                          # Get the data
        return opcode, blocknr, data
    elif opcode == OPCODE_ACK:
        blocknr = struct.unpack("!H", msg[2:4]) # Extract blocknr
        arg = "None"                            # Added arg just for handling in tftp_tranfer
        return opcode, blocknr, arg
    elif opcode == OPCODE_ERR:
        errorcode = struct.unpack("!H", msg[2:4])  # Get error code
        errormsg = msg[4:].split('\0')             # Get error message
        return opcode, errorcode, errormsg
    else: 
        return ERROR_CODES[1]                   # When all else fail: Return Undef error
    return None
    
def tftp_transfer(fd, hostname, direction, filename):
   
    TFTP_PORT= 6969 # Port with no simulated package loss
    TFTP_PORT_LOSS = 10069 # Port with simulated loss
    TFTP_PORT_DUPL = 20069 # Port with duplicate acks
    TFTP_LOSS_PORT10 = 11069  # Port with 10% simulated package loss
    TFTP_LOSS_PORT20 = 12069  # Port with 20% -----
    TFTP_LOSS_PORT30 = 13069  # Port with 30% -----
  
    

    server_addr = socket.getaddrinfo(hostname, TFTP_PORT)[0][4:][0] # Get server info, like IP and port
    server_addr_ip = server_addr[0]
    server_addr_port = server_addr[1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Initiate socket
    sock.settimeout(TFTP_TIMEOUT) # One way of adding timeout to the socket

    # Check if we are putting a file or getting a file and send
    # the corresponding request.
    try: 
        total_file_sent = 0
        if direction == TFTP_GET: #We want to get a file
            message = make_packet_rrq(filename, MODE_OCTET)
            sock.sendto(message, server_addr)
            last_recieved = 0

        elif direction == TFTP_PUT: #We want to put a file
            message = make_packet_wrq(filename, MODE_OCTET)
            sock.sendto(message, server_addr)
            packetnr = 0
            timeoutnr = 0


    except Exception, Excepterror: #Handle exceptions
            if (Excepterror == 'timed out') == True: 
                print "Send error in request action"
                print Excepterror
            else: 
                sock.sendto(message, server_addr)
                print "Resent message because of timeout"
    
    # Put or get the file, block by block, in a loop.
    while True:
        readable, writable, exceptional = select.select([sock], [], [], TFTP_TIMEOUT)
        if direction == TFTP_GET:
            try:   
                if readable > 0: # Check if socket has received complete package
                    chunk_of_data, server_addr = sock.recvfrom(516) # Get package and return adress from socket buffer
                    opcode, blocknr, arg = parse_packet(chunk_of_data) # Unpack message
                    if opcode == OPCODE_DATA and len(arg) >= BLOCK_SIZE and last_recieved == blocknr[0]-1: # Not last chunk to be transfered and the package is the next in order
                        print "Sent ack with nr " + str(blocknr[0])
                        message = make_packet_ack(blocknr[0])
                        sock.sendto(message, server_addr)
                        fd.write(arg)
                        last_recieved = blocknr[0]
                    elif opcode == OPCODE_DATA and len(arg) < BLOCK_SIZE and last_recieved == blocknr[0]-1: # Last chunk to be transfered and the package is the next in order
                        print "Sent ack with nr " + str(blocknr[0])
                        message = make_packet_ack(blocknr[0])
                        sock.sendto(message, server_addr)
                        fd.write(arg)
                        last_recieved = blocknr[0]
                        print "End of transfer"
                        break
                    elif opcode == OPCODE_ERR:
                        print "Opcode: " + str(opcode) + " Errormsg: " + str(arg[0]) # Error handling, returns error code and message
                        break
                    else:
                        message = make_packet_ack(last_recieved) # Not the correct chunk recieved, resend latest correct ack
                        sock.sendto(message, server_addr)
                else:
                    print "Recieve timeout TFTP_TIMEOUT sec"
                    #sock.Timeout(TFTP_TIMEOUT)

            except Exception, Excepterror:
                if (Excepterror == 'timed out') == True: 
                    print "Failed miserably"
                    print Excepterror
                    break
                         
                else:
                    sock.sendto(message, server_addr) # Resend message because of timeout
        
            
        elif direction == TFTP_PUT:
            try:
                if readable > 0: # Check if socket has received complete package
                    chunk_of_data, server_addr = sock.recvfrom(516) # Get package and return adress from socket buffer
                    opcode, blocknr, arg = parse_packet(chunk_of_data)
                    if opcode == OPCODE_ACK and blocknr[0] == packetnr: # Check so it's the ack for the latest sent chunk
                        chunk_to_be_sent = fd.read(BLOCK_SIZE)
                        packetnr = packetnr+1
                        if len(chunk_to_be_sent) >= BLOCK_SIZE:   # Check so we aren't in the end of file = not last chunk
                            print "Sent packet nr: " + str(packetnr)
                            message = make_packet_data(packetnr, chunk_to_be_sent)
                            sock.sendto(message, server_addr)
                            timeoutnr = 0
                        elif len(chunk_to_be_sent) < BLOCK_SIZE: # Last chunk to be sent, take the last data and make a chunk of it
                            message = make_packet_data(packetnr, chunk_to_be_sent)
                            sock.sendto(message, server_addr)
                            print "Sent packet nr: " + str(packetnr)
                            timeoutnr = 0
                            total_file_sent = 1
                        else: 
                            print "Something with packaging in put went wrong"
                    elif opcode == OPCODE_ACK and blocknr[0] != packetnr: # Latest ack was not correct, resend message
                        sock.sendto(message, server_addr)

                    else: 
                        print "Opcode: " + str(opcode) + " Errormsg: " + str(arg[0]) # Error handling, returns error code and message
                        break

                else:
                    print "Send timeout TFTP_TIMEOUT sec" 
                   # sock.Timeout(TFTP_TIMEOUT) # Time out for the socket if the message haven't been completly delivered

            except Exception, Excepterror: # Handle exceptions
                if (Excepterror == 'timed out') == True: 
                    print "Runtime exception error, see print: "
                    print Excepterror
                    break    
                elif timeoutnr == 3 and total_file_sent == 1: # Total file sent and made sure that last package have arrived
                    print "Total file sent"
                    break
                elif timeoutnr < 3:
                    sock.sendto(message, server_addr) # Resend because of timeout!
                    timeoutnr = timeoutnr + 1
                else: 
                    print "Terminate because of timeout"
        else: 
            print "Total breakdown in put. Should not have been able to get here. Line 214." # When all else fails!
            break
            

                
        #sock.close()
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
