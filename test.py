import serial
from serial import tools
from serial.tools import list_ports


def available_ttys():
    for tty in serial.tools.list_ports.comports():
        try:
            port = serial.Serial(port=tty[0])
            if port.isOpen():
                yield port
        except serial.SerialException as ex:
            print ('Port %s is unavailable: %s' % (tty, ex))


def main():
    ttys = []
    for tty in available_ttys():
        ttys.append(tty)
        print (tty)

    input('waiting ...')


if __name__ == '__main__':
    main()