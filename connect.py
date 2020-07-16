#  coding: utf-8
import paramiko
import time
import telnetlib
import sys
import sundry as s
import pprint
import traceback
import consts



class ConnSSH(object):
    '''
    ssh connect to VersaPLX
    '''

    def __init__(self, host, port, username, password, timeout):
        self.logger = consts.glo_log()
        self.logger.d1 = host
        self._host = host
        self._port = port
        self._timeout = timeout
        self._username = username
        self._password = password
        self.SSHConnection = None
        self._connect()

    def _connect(self):
        self.logger.write_to_log('T', 'INFO', 'info', 'start', '', '  Start to connect VersaPLX via SSH')
        self.logger.write_to_log('F', 'DATA', 'value', 'dict', 'data for SSH connect',
                                 {'host': self._host, 'port': self._port, 'username': self._username,
                                  'password': self._password})

        try:
            objSSHClient = paramiko.SSHClient()
            objSSHClient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            objSSHClient.connect(self._host, port=self._port,
                                 username=self._username,
                                 password=self._password,
                                 timeout=self._timeout)
            # 连接成功log记录？
            self.SSHConnection = objSSHClient
        except Exception as e:
            self.logger.write_to_log('F', 'DATA', 'debug', 'exception', 'ssh connect', str(traceback.format_exc()))
            s.pwe(f'  Connect to {self._host} failed with error: {e}')

    def execute_command(self, command):
        # oprt_id = s.get_oprt_id()
        # self.logger.write_to_log('T','OPRT','cmd','ssh',oprt_id,command)
        stdin, stdout, stderr = self.SSHConnection.exec_command(command)
        data = stdout.read()
        if len(data) > 0:
            output = {'sts': 1, 'rst': data}
            return output
        err = stderr.read()
        if len(err) > 0:
            output = {'sts': 0, 'rst': err}
            self.logger.write_to_log('T', 'INFO', 'warning', 'failed', '', f'  Command "{command}" execute failed')
            return output
        if data == b'':
            output = {'sts': 1, 'rst': data}
            return output

    def ssh_connect(self):
        self._connect()
        if not self.SSHConnection:
            self.logger.write_to_log('T', 'INFO', 'info', 'start', '', '  Retry connect to VersaPLX via SSH')
            self._connect()

    def close(self):
        self.SSHConnection.close()
        self.logger.write_to_log('T', 'INFO', 'info', 'finish', '', 'Close SSH connection')


class ConnTelnet(object):
    '''
    telnet connect to NetApp
    '''

    def __init__(self, host, port, username, password, timeout):
        self.logger = consts.glo_log()
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._timeout = timeout
        self.telnet = telnetlib.Telnet()
        self.telnet_connect()

    def _connect(self):
        try:
            self.logger.write_to_log('T', 'INFO', 'info', 'start', '', '  Start to connect NetApp via telnet')
            self.logger.write_to_log('F', 'DATA', 'value', 'dict', 'data for telnet connect',
                                     {'host': self._host, 'port': self._port, 'username': self._username,
                                      'password': self._password})
            self.telnet.open(self._host, self._port)
            self.telnet.read_until(b'Username:', timeout=1)
            self.telnet.write(self._username.encode() + b'\n')
            self.telnet.read_until(b'Password:', timeout=1)
            self.telnet.write(self._password.encode() + b'\n')

        except Exception as e:
            self.logger.write_to_log('F', 'DATA', 'debug', 'exception', 'telnet connect', str(traceback.format_exc()))
            s.pwe(f'  Connect to {self._host} failed with error: {e}')

    # 定义exctCMD函数,用于执行命令
    def execute_command(self, cmd):
        'executr command only on FAS270'
        oprt_id = s.get_oprt_id()
        self.logger.write_to_log('T', 'OPRT', 'cmd', 'telnet', oprt_id, cmd)
        self.telnet.read_until(b'fas270>').decode()
        self.telnet.write(cmd.encode().strip() + b'\r')
        rely = self.telnet.read_until(b'fas270>').decode()
        self.telnet.write(b'\r')
        return rely

    def telnet_connect(self):
        self._connect()
        if not self.telnet:
            self._connect()

    def close(self):
        self.telnet.close()
        self.logger.write_to_log('INFO', 'info', '', 'Close Telnet connection.')


if __name__ == '__main__':
    # telnet
    # host = '10.203.1.231'
    # port = '22'
    # username = 'root'
    # password = 'Feixi@123'
    # timeout = 5
    # ssh = ConnSSH(host, port, username, password, timeout)
    # strout = ssh.execute_command('?')
    # w = strout.decode('utf-8')
    # print(type(w))
    # print(w.split('\n'))
    # pprint.pprint(w)
    # time.sleep(2)
    # strout = ssh.execute_command('lun show -m')
    # pprint.pprint(strout)

    pass