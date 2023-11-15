import warnings

import serial
import sys
import glob
import numpy as np
from itertools import product


def find_serial():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result


class SerialManager:
    def __init__(self, commport: str, baudrate: int, num_channel: int = 1,
                 window_size: int = 1, EOL: str = None):
        """ Initialize SerialManager class - manages functions related to instantiating and using serial port

        :param commport: target serial port
        :param baudrate: target baudrate
        :param num_channel: number of distinct channels
        :param window_size: for 1D & 2D data, number of timepoints to acquire before passing
        :param EOL: optional; end of line phrase used to separate timepoints
        """
        self.commport = commport
        self.baudrate = baudrate
        self.num_channel = num_channel
        self.window_size = window_size
        self.EOL = EOL
        self.ser = None

    def setup_serial(self):
        """ Sets up given serial port for a given baudrate

        :return: serial object
        """
        try:
            self.ser = serial.Serial(self.commport, self.baudrate, timeout=0.1)
            return self.ser
        except (OSError, serial.SerialException):
            raise OSError("Error setting up serial port")

    def check_ser_data(self, ser_data: np.ndarray):
        """ Function to check quality of acquired serial data
        :param ser_data: acquired serial data to be checked for correct dimension
        """
        ser_data_shape = np.shape(ser_data)
        if self.window_size != ser_data_shape[0]:
            warnings.warn(f"number of rows in serial data should be {self.window_size}\n"
                          f"acquired serial data has {ser_data_shape[0]}")

        if self.num_channel != ser_data_shape[1]:
            raise ValueError(f"acquired serial data must have the {self.num_channel} channels of data\n"
                             f"Each channel must be a column in serial function output. \n"
                             f"current serial function output is {ser_data}")

    def _acquire_data(self):
        """Handler function to acquire serial port data
        Confirms validity of incoming data

        :return: channel data [shape: (self.window_size, self.num_channel)]

        """
        ser_data = np.zeros((self.window_size, self.num_channel))
        channel_data = np.array([])
        # Decode incoming data into ser_data array
        if self.EOL is None:
            for i in product((range(self.window_size)), range(self.num_channel)):
                try:
                    ser_data[i] = self.ser.readline().decode().strip()
                except ValueError:
                    pass
        else:
            # TODO: EOL Handler
            pass
        # If any zeros
        for i in range(self.window_size):
            if any(ser_data[i, :] == 0):
                pass
            else:
                channel_data = np.append(channel_data, ser_data[i][:])

        channel_data = np.reshape(channel_data, (int(len(channel_data) / self.num_channel), self.num_channel))

        return channel_data

    def acquire_data(self, func=None):
        """ Acquire serial port data
        :param func: if None, defaults to using _acquire_data func. otherwise, use custom func to process ser data

        :return: channel data [shape: (self.window_size, self.num_channel)]
        """
        if self.ser is None:
            raise ValueError(f"serial port {self.ser} must be instantiated before acquiring data\n"
                             f"please run setup_serial()")
        if func is None:
            channel_data = self._acquire_data()
        else:
            try:
                channel_data = func(ser=self.ser)
            except:
                raise ValueError(f'custom function {func} must have the the serial port object referenced as ser')

        self.check_ser_data(ser_data=channel_data)

        if channel_data.size > 0:
            return channel_data
        else:
            return
