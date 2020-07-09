import asyncio
import sys

from functools import reduce
from operator import xor

from serial import PARITY_EVEN, PARITY_NONE, PARITY_ODD
from serial.tools.list_ports import comports

from serial_asyncio import create_serial_connection

from PyQt5.QtWidgets import QWidget, QApplication, QVBoxLayout, QPushButton, QHBoxLayout, QLineEdit, QComboBox, \
    QLabel, QPlainTextEdit


def compute_fcs(msg):
    return format(reduce(xor, map(ord, msg)), 'x')


class TurBoHostLink(QWidget):

    def __init__(self, loop, parent=None):
        super(TurBoHostLink, self).__init__(parent)

        self.setGeometry(0, 0, 600, 0)

        self.setWindowTitle('TurBoHostLink')

        self.loop = loop

        self.serial_coro = None

        self.main_layout = QHBoxLayout()
        self.config_layout = QVBoxLayout()
        self.console_layout = QVBoxLayout()

        self.port_label = QLabel(text="Port:")
        self.bauds_label = QLabel(text="Bauds Rate:")
        self.data_bits_label = QLabel(text="Data Bits:")
        self.parity_label = QLabel(text="Parity:")
        self.stop_bits_label = QLabel(text="Stop Bits:")
        self.unit_number_label = QLabel(text="Unit Number:")

        self.serial_port = QComboBox()
        self.enumerate_ports()

        self.serial_bauds = QComboBox()

        for baud_rate in (9600, 19200, 38400, 57600, 115200):
            self.serial_bauds.addItem(str(baud_rate), baud_rate)

        self.serial_data_bits = QComboBox()

        self.serial_data_bits.addItem("7", 7)
        self.serial_data_bits.addItem("8", 8)

        self.serial_parity = QComboBox()

        self.serial_parity.addItem("None", PARITY_NONE)
        self.serial_parity.addItem("Odd", PARITY_ODD)
        self.serial_parity.addItem("Even", PARITY_EVEN)

        self.serial_stop_bits = QComboBox()
        self.serial_stop_bits.addItem("1", 1)
        self.serial_stop_bits.addItem("2", 2)

        self.unit_number = QLineEdit()
        self.unit_number.setText("00")

        self.connect_button = QPushButton()
        self.connect_button.setText("Connect")
        self.connect_button.setDisabled(False)

        self.disconnect_button = QPushButton()
        self.disconnect_button.setText("Disconnect")
        self.disconnect_button.setDisabled(True)

        self.cmd_label = QLabel(text="Command:")
        self.msg_label = QLabel(text="Message:")
        self.fcs_label = QLabel(text="FCS:")
        self.output_label = QLabel(text="Output:")

        self.cmd_field = QLineEdit()
        self.msg_field = QLineEdit()
        self.fcs_field = QLineEdit()
        self.output_field = QLineEdit()

        self.send_button = QPushButton()
        self.send_button.setText("Send")
        self.send_button.setDisabled(True)

        self.response_field = QPlainTextEdit()

        self.config_layout.addWidget(self.port_label)
        self.config_layout.addWidget(self.serial_port)
        self.config_layout.addWidget(self.bauds_label)
        self.config_layout.addWidget(self.serial_bauds)
        self.config_layout.addWidget(self.data_bits_label)
        self.config_layout.addWidget(self.serial_data_bits)
        self.config_layout.addWidget(self.parity_label)
        self.config_layout.addWidget(self.serial_parity)
        self.config_layout.addWidget(self.stop_bits_label)
        self.config_layout.addWidget(self.serial_stop_bits)
        self.config_layout.addWidget(self.unit_number_label)
        self.config_layout.addWidget(self.unit_number)
        self.config_layout.addWidget(self.connect_button)
        self.config_layout.addWidget(self.disconnect_button)

        self.console_layout.addWidget(self.cmd_label)
        self.console_layout.addWidget(self.cmd_field)
        self.console_layout.addWidget(self.msg_label)
        self.console_layout.addWidget(self.msg_field)
        self.console_layout.addWidget(self.fcs_label)
        self.console_layout.addWidget(self.fcs_field)
        self.console_layout.addWidget(self.output_label)
        self.console_layout.addWidget(self.output_field)
        self.console_layout.addWidget(self.send_button)
        self.console_layout.addWidget(self.response_field)

        self.main_layout.addLayout(self.config_layout)
        self.main_layout.addLayout(self.console_layout)

        self.setLayout(self.main_layout)

        self.connect_button.clicked.connect(self.open_port)
        self.disconnect_button.clicked.connect(self.close_port)

        self.unit_number.textChanged.connect(self.update_output)
        self.cmd_field.textChanged.connect(self.update_output)
        self.msg_field.textChanged.connect(self.update_output)
        self.send_button.clicked.connect(self.send_message)

    def send_message(self):
        message = self.output_field.text()
        print(message)

    def update_output(self):
        header = "@"
        node = self.unit_number.text()
        cmd = self.cmd_field.text()
        msg = self.msg_field.text()
        fcs = compute_fcs(f'@{node}{cmd}{msg}')
        terminator = "*\r"

        self.fcs_field.setText(fcs)
        self.output_field.setText(f"{header}{node}{cmd}{msg}{fcs}{terminator}")

    def enumerate_ports(self):
        for port in comports(include_links=False):
            self.serial_port.addItem(f"{port[0]} {port.description}", port)

    def open_port(self):
        port = self.serial_port.currentData()
        data_bits = self.serial_data_bits.currentData()
        stop_bits = self.serial_stop_bits.currentData()
        parity = self.serial_parity.currentData()
        bauds = self.serial_bauds.currentData()

        self.serial_coro = create_serial_connection(self.loop,
                                                    Output,
                                                    url=port[0],
                                                    bytesize=data_bits,
                                                    stopbits=stop_bits,
                                                    parity=parity,
                                                    baudrate=bauds,
                                                    timeout=0.25)

        asyncio.ensure_future(self.serial_coro)

        self.connect_button.setDisabled(True)
        self.disconnect_button.setDisabled(False)
        self.send_button.setDisabled(False)

    def close_port(self):
        self.loop.stop()
        self.connect_button.setDisabled(False)
        self.disconnect_button.setDisabled(True)
        self.send_button.setDisabled(True)

    async def send(self, w, msgs):
        for msg in msgs:
            w.write(msg)
            print(f'sent: {msg.decode().rstrip()}')
            await asyncio.sleep(0.5)
        w.write(b'DONE\n')
        print('Done sending')

    async def recv(self, r):
        print(r)
        while True:
            msg = await r.readuntil(b'\n')
            if msg.rstrip() == b'DONE':
                print('Done receiving')
                break
            print(f'received: {msg.rstrip().decode()}')


class Output(asyncio.Protocol):
    def connection_made(self, transport):
        self.transport = transport
        print('port opened', transport)

        node = '00'
        header = 'TS'
        data = '1337'
        message = f'@{node}{header}{data}'
        fcs = compute_fcs(message)
        terminator = '*\r'

        # transport.serial.rts = False  # You can manipulate Serial object via transport
        transport.serial.write(message.encode("ascii"))
        transport.serial.write(fcs.encode("ascii"))
        transport.serial.write(terminator.encode("ascii"))

    def data_received(self, data):
        print('data received', repr(data))
        if b'\r' in data:
            self.transport.close()

    def connection_lost(self, exc):
        print('port closed')
        self.transport.loop.stop()

    def pause_writing(self):
        print('pause writing')
        print(self.transport.get_write_buffer_size())

    def resume_writing(self):
        print(self.transport.get_write_buffer_size())
        print('resume writing')


class Writer(asyncio.Protocol):
    def connection_made(self, transport):
        """Store the serial transport and schedule the task to send data.
        """
        self.transport = transport
        print('Writer connection created')
        asyncio.ensure_future(self.send())
        print('Writer.send() scheduled')

    def connection_lost(self, exc):
        print('Writer closed')

    async def send(self):
        """Send four newline-terminated messages, one byte at a time.
        """
        message = b'foo\nbar\nbaz\nqux\n'
        for b in message:
            await asyncio.sleep(0.5)
            self.transport.serial.write(bytes([b]))
            print(f'Writer sent: {bytes([b])}')
        self.transport.close()


class Reader(asyncio.Protocol):
    def connection_made(self, transport):
        """Store the serial transport and prepare to receive data.
        """
        self.transport = transport
        self.buf = bytes()
        self.msgs_recvd = 0
        print('Reader connection created')

    def data_received(self, data):
        """Store characters until a newline is received.
        """
        self.buf += data
        if b'\n' in self.buf:
            lines = self.buf.split(b'\n')
            self.buf = lines[-1]  # whatever was left over
            for line in lines[:-1]:
                print(f'Reader received: {line.decode()}')
                self.msgs_recvd += 1
        if self.msgs_recvd == 4:
            self.transport.close()

    def connection_lost(self, exc):
        print('Reader closed')


async def main(loop):
    app = QApplication(sys.argv)

    term = TurBoHostLink(loop)
    term.show()

    app.exec_()


loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
loop.close()
