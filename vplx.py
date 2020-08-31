#  coding: utf-8
import connect
import sundry as s
import time
import consts
import log
import re

SSH = None

HOST = '10.203.1.199'
PORT = 22
USER = 'root'
PASSWORD = 'password'
TIMEOUT = 3

NETAPP_IP = '10.203.1.231'
TARGET_IQN = "iqn.2020-06.com.example:test-max-lun"
TARGET_NAME = 't_test'
PORTBLOCK_UNBLOCK_NAME="p_iscsi_portblock_off"


def init_ssh():
    global SSH
    if not SSH:
        SSH = connect.ConnSSH(HOST, PORT, USER, PASSWORD, TIMEOUT)

class DebugLog(object):
    def __init__(self):
        init_ssh()
        self.tid = consts.glo_tsc_id()
        self.debug_folder = f'/var/log/{self.tid}'
        self.dbg = s.DebugLog(SSH, self.debug_folder, HOST)

    def collect_debug_sys(self):
        cmd_debug_sys = consts.get_cmd_debug_sys(self.debug_folder, HOST)
        self.dbg.prepare_debug_log(cmd_debug_sys)

    def collect_debug_drbd(self):
        cmd_debug_drbd = consts.get_cmd_debug_drbd(self.debug_folder, HOST)
        self.dbg.prepare_debug_log(cmd_debug_drbd)

    def collect_debug_crm(self):
        cmd_debug_crm = consts.get_cmd_debug_crm(self.debug_folder, HOST)
        self.dbg.prepare_debug_log(cmd_debug_crm)

    def get_all_log(self, folder):
        local_file = f'{folder}/{HOST}.tar'
        self.dbg.get_debug_log(local_file)


class VplxDrbd(object):
    '''
    Integrate LUN in DRBD resources
    '''
    def __init__(self):
        self.logger = consts.glo_log()
        self.rpl = consts.glo_rpl()
        self.id = None
        self.str = None
        self._prepare()
        self.iscsi=s.Iscsi(SSH,NETAPP_IP)

    def _prepare(self):
        if self.rpl == 'no':
            init_ssh()

    def cfg(self):
        s.pwl('Start to configure DRDB resource and CRM resource on VersaPLX', 0, s.get_oprt_id(), 'start')
        s.pwl('Start to configure DRBD resource', 2, '', 'start')
        self.res_name = f'res_{self.str}_{self.id}'
        global DRBD_DEV_NAME
        DRBD_DEV_NAME = f'drbd{self.id}'
        self._add_config_file()  # 创建配置文件
        self._init()
        self._up()
        self._primary()
        self.status_verify()  # 验证有没有启动（UptoDate）

    def _add_config_file(self):
        '''
        Prepare DRDB resource config file
        '''
        blk_dev_name = s.GetNewDisk.get_disk_from_netapp(SSH)
        self._create_config_file(blk_dev_name)

    def _create_config_file(self, blk_dev_name):
        s.pwl(f'Start to prepare DRBD config file "{self.res_name}.res"', 3, '', 'start')
        context = [rf'resource {self.res_name} {{',
                   rf'\ \ \ \ on maxluntarget {{',
                   rf'\ \ \ \ \ \ \ \ device /dev/{DRBD_DEV_NAME}\;',
                   rf'\ \ \ \ \ \ \ \ disk {blk_dev_name}\;',
                   rf'\ \ \ \ \ \ \ \ address 10.203.1.199:7789\;',
                   rf'\ \ \ \ \ \ \ \ node-id 0\;',
                   rf'\ \ \ \ \ \ \ \ meta-disk internal\;',
                   r'\ \ \ \}',
                   r'}']
        if self.rpl == 'yes':
            return
        self.logger.write_to_log(
            'F', 'DATA', 'value', 'list', 'content of drbd config file', context)
        unique_str = 'UsKyYtYm1'
        config_file_name = f'{self.res_name}.res'
        for i in range(len(context)):
            if i == 0:
                oprt_id = s.get_oprt_id()
                cmd = f'echo {context[i]} > /etc/drbd.d/{config_file_name}'
                echo_result = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
            else:
                oprt_id = s.get_oprt_id()
                cmd = f'echo {context[i]} >> /etc/drbd.d/{config_file_name}'
                echo_result = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
            if echo_result['sts']:
                continue
            else:
                s.pwce('Failed to prepare DRBD config file..', 4, 2)

        s.pwl(f'Succeed in creating DRBD config file "{self.res_name}.res"', 4, '', 'finish')

    def _init(self):
        '''
        Initialize DRBD resource
        '''
        oprt_id = s.get_oprt_id()
        unique_str = 'usnkegs'
        cmd = f'drbdadm create-md {self.res_name}'
        info_msg = f'Start to initialize DRBD resource for "{self.res_name}"'
        s.pwl(info_msg, 3, oprt_id, 'start')
        init_result = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        re_drbd = 'New drbd meta data block successfully created'
        if init_result:
            if init_result['sts']:
                re_result = s.re_search(re_drbd, init_result['rst'].decode())
                if re_result:
                    s.pwl(f'Succeed in initializing DRBD resource "{self.res_name}"', 4, oprt_id, 'finish')
                    return True
                else:
                    s.pwce(f'Failed to initialize DRBD resource {self.res_name}', 4, 2)
        else:
            s.handle_exception()

    def _up(self):
        '''
        Start DRBD resource
        '''
        oprt_id = s.get_oprt_id()
        unique_str = 'elsflsnek'
        cmd = f'drbdadm up {self.res_name}'
        s.pwl(f'Start to bring up DRBD resource "{self.res_name}"', 3, oprt_id, 'start')
        result = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        if result:
            if result['sts']:
                s.pwl(f'Succeed in bringing up DRBD resource "{self.res_name}"', 4, oprt_id, 'finish')
                return True
            else:
                s.pwce(f'Failed to bring up resource {self.res_name}', 4, 2)
        else:
            s.handle_exception()

    def _primary(self):
        '''
        Complete initial synchronization of resources
        '''
        oprt_id = s.get_oprt_id()
        unique_str = '7C4LU6Xr'
        cmd = f'drbdadm primary --force {self.res_name}'
        s.pwl(f'Start to initial synchronization for "{self.res_name}"', 3, oprt_id, 'start')
        result = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        if result:
            if result['sts']:
                s.pwl(f'Succeed in synchronizing DRBD resource "{self.res_name}"', 4, oprt_id, 'finish')
                return True
            else:
                s.pwce(f'Failed to synchronize resource {self.res_name}', 4, 2)
        else:
            s.handle_exception()

    def status_verify(self):
        '''
        Check DRBD resource status and confirm the status is UpToDate
        '''
        oprt_id = s.get_oprt_id()
        cmd = f'drbdadm status {self.res_name}'
        s.pwl(f'Start to check DRBD resource "{self.res_name}" status', 3, oprt_id, 'start')
        result = s.get_ssh_cmd(SSH, 'By91GFxC', cmd, oprt_id)
        if result:
            if result['sts']:
                result = result['rst'].decode()
                re_display = r'''disk:(\w*)'''
                re_result = s.re_search(re_display, result)
                if re_result:
                    status = re_result.group(1)
                    if status == 'UpToDate':
                        s.pwl(f'Succeed in checking DRBD resource "{self.res_name}"', 4, oprt_id, 'finish')
                        return True
                    else:
                        s.pwce(f'Failed to check DRBD resource "{self.res_name}"', 4, 2)
                else:
                    s.pwce(f'DRBD {self.res_name} does not exist', 4, 2)
        else:
            s.handle_exception()

    def _down(self, res_name):
        '''
        Stop the DRBD resource
        '''
        unique_str = 'UqmYgtM3'
        drbd_down_cmd = f'drbdadm down {res_name}'
        oprt_id = s.get_oprt_id()
        down_result = s.get_ssh_cmd(SSH, unique_str, drbd_down_cmd, oprt_id)
        if down_result['sts']:
            s.pwl(f'Down the DRBD resource "{res_name}" successfully',2)
            return True
        else:
            s.pwce(f'Failed to stop DRBD "{res_name}"', 4, 2)

    def _del_config(self, res_name):
        '''
        remove the DRBD config file
        '''
        unique_str = 'UqkYgtM3'
        drbd_del_cmd = f'rm /etc/drbd.d/{res_name}.res'
        oprt_id = s.get_oprt_id()
        del_result = s.get_ssh_cmd(SSH, unique_str, drbd_del_cmd, oprt_id)
        if del_result['sts']:
            s.pwl(f'Removed the DRBD resource "{res_name}" config file successfully',2)
            return True
        else:
            s.pwce('Failed to remove DRBD config file', 4, 2)

    def get_all_cfgd_drbd(self):
        # get list of all configured crm res
        cmd_drbd_status = 'drbdadm status'
        show_result = s.get_ssh_cmd(SSH, 'UikYgtM1', cmd_drbd_status, s.get_oprt_id())
        if show_result:
            if show_result['sts']:
                re_drbd = f'res_\w*_[0-9]{{1,3}}'
                show_result = show_result['rst'].decode('utf-8')
                drbd_cfgd_list = s.re_findall(re_drbd, show_result)
                return drbd_cfgd_list
            else:
                s.pwe(f'Failed to execute command "{cmd_drbd_status}"', 3, 2)
        else:
            s.handle_exception()

    def _del(self, res_name):
        s.pwl(f'Deleting DRBD resource {res_name}',1)
        if self._down(res_name):
            if self._del_config(res_name):
                return True

    def del_drbds(self, drbd_to_del_list):
        if drbd_to_del_list:
            s.pwl('Start to delete DRBD resource',0)
            for res_name in drbd_to_del_list:
                self._del(res_name)


class VplxCrm(object):
    def __init__(self):
        self.logger = consts.glo_log()
        self.rpl = consts.glo_rpl()
        self.id = None
        self.str = None
        if self.rpl == 'no':
            init_ssh()

    def cfg(self):
        self.lu_name = f'res_{self.str}_{self.id}'
        s.pwl('Start to configure crm resource', 2, '', 'start')
        self._create()
        self._setting()
        self._start()
        time.sleep(0.5)
        self._status_verify()
        return True

    def modify_initiator_and_verify(self):
        self.lu_name = f'res_{self.str}_{self.id}'
        self._modify_allow_initiator()
        self._crm_and_targetcli_verify()


    def _create(self):
        '''
        Create iSCSILogicalUnit resource
        '''
        oprt_id = s.get_oprt_id()
        if consts.glo_iqn_list():
            initiator_iqn=' '.join(consts.glo_iqn_list())
        else:
            s.pwe('Global IQN list is None',2,2)
        unique_str = 'LXYV7dft'
        s.pwl(f'Start to create iSCSILogicalUnit resource "{self.lu_name}"', 3, oprt_id, 'start')
        cmd = f'crm conf primitive {self.lu_name} \
            iSCSILogicalUnit params target_iqn="{TARGET_IQN}" \
            implementation=lio-t lun={consts.glo_id()} path="/dev/{DRBD_DEV_NAME}"\
            allowed_initiators="{initiator_iqn}" op start timeout=600 interval=0 op stop timeout=600 interval=0 op monitor timeout=40 interval=50 meta target-role=Stopped'#40->600
        result = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        if result:
            if result['sts']:
                s.pwl(f'Succeed in creating iSCSILogicaLUnit "{self.lu_name}"', 4, oprt_id, 'finish')
                return True
            else:
                s.pwce(f'Failed to create iSCSILogicaLUnit "{self.lu_name}"', 4, 2)
        else:
            s.handle_exception()

    def _set_col(self):
        '''
        Setting up iSCSILogicalUnit resources of colocation
        '''
        oprt_id = s.get_oprt_id()
        unique_str = 'E03YgRBd'
        cmd = f'crm conf colocation co_{self.lu_name} inf: {self.lu_name} {TARGET_NAME}'
        s.pwl(f'Start to set up colocation of iSCSILogicalUnit "{self.lu_name}"', 3, oprt_id, 'start')
        result_crm = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        if result_crm:
            if result_crm['sts']:
                s.pwl(f'Succeed in setting colocation of "{self.lu_name}"', 4, oprt_id, 'finish')
                return True
            else:
                s.pwce(f'Failed to set colocation of "{self.lu_name}"', 4, 2)
        else:
            s.handle_exception()

    def _set_order(self):
        '''
        Setting up iSCSILogicalUnit resources of order
        '''
        oprt_id = s.get_oprt_id()
        unique_str = '0GHI63jX'
        cmd = f'crm conf order or_{self.lu_name} {TARGET_NAME} {self.lu_name}'
        s.pwl(f'Start to set up order of iSCSILogicalUnit "{self.lu_name}"', 3, oprt_id, 'start')
        result_crm = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        if result_crm:
            if result_crm['sts']:
                s.pwl(f'Succeed in setting order of "{self.lu_name}"', 4, oprt_id, 'finish')
                return True
            else:
                s.pwce(f'Failed to set order of "{self.lu_name}"', 4, 2)
        else:
            s.handle_exception()
    
    def _set_portblock(self):
        oprt_id=s.get_oprt_id()
        unique_str='TgFqUiOkl'
        cmd=f'crm conf order or_{self.lu_name}_prtoff {self.lu_name} {PORTBLOCK_UNBLOCK_NAME}'
        s.pwl(f'Start to set up portblock of iSCSILogicalUnit "{self.lu_name}"', 3, oprt_id, 'start')
        results=s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        if results:
            if results['sts']:
                s.pwl(f'Succeed in setting portblock of "{self.lu_name}"', 4, oprt_id, 'finish')
                return True
            else:
                s.pwce(f'Failed to set portblock of "{self.lu_name}"', 4, 2)
        else:
            s.handle_exception()

    def _setting(self):
        if self._set_col():
            if self._set_order():
                if self._set_portblock():
                    return True

    def _start(self):
        '''
        start up the iSCSILogicalUnit resource
        '''
        oprt_id = s.get_oprt_id()
        unique_str = 'YnTDsuVX'
        cmd = f'crm res start {self.lu_name}'
        s.pwl(f'Start up the iSCSILogicalUnit resource "{self.lu_name}"', 3, oprt_id, 'start')
        result_cmd = s.get_ssh_cmd(SSH, unique_str, cmd, oprt_id)
        if result_cmd:
            if result_cmd['sts']:
                    return True
            else:
                s.pwce(f'Failed to start up iSCSILogicaLUnit "{self.lu_name}"', 4, 2)
        else:
            s.handle_exception()
    
    def _status_verify(self):
        oprt_id = s.get_oprt_id()
        if self._cyclic_check_crm_status(self.lu_name,'Started',6,100):
            s.pwl(f'Succeed in starting up iSCSILogicaLUnit "{self.lu_name}"', 4, oprt_id, 'finish')
            return True
        else:
            s.pwce(f'Failed to start up iSCSILogicaLUnit "{self.lu_name}"', 4, 2)

    def _get_crm_status(self, res_name):
        '''
        Check the crm resource status
        '''
        unique_str = 'UqmUytK3'
        crm_show_cmd = f'crm res list | grep {res_name}'
        oprt_id = s.get_oprt_id()
        verify_result = s.get_ssh_cmd(SSH, unique_str, crm_show_cmd, oprt_id)
        if verify_result:
            if verify_result['sts']:
                re_string=f'''{res_name}\s*\(ocf::heartbeat:\w*\):\s*(\w*)'''
                re_result=s.re_search(re_string, verify_result['rst'].decode('utf-8'))
                if re_result:
                    return {'status': re_result.group(1)}
                else:
                    s.pwce('Failed to show crm',4,2)
            else:
                s.pwce('Failed to show crm',4,2)
        else:
            s.handle_exception()

    def _cyclic_check_crm_status(self, res_name, expect_status,sec, num):
        '''
        Determine crm resource status is started/stopped
        '''
        n = 0
        while n < num:
            n += 1
            if self._get_crm_status(res_name)['status'] != expect_status:
                time.sleep(sec)
            else:
                return True

    def _stop(self, res_name):
        '''
        stop the iSCSILogicalUnit resource
        '''
        unique_str = 'UqmYgtM1'
        crm_stop_cmd = (f'crm res stop {res_name}')
        oprt_id = s.get_oprt_id()
        crm_stop = s.get_ssh_cmd(SSH, unique_str, crm_stop_cmd, oprt_id)
        if crm_stop:
            if crm_stop['sts']:
                if self._cyclic_check_crm_status(res_name, 'Stopped',6,100):
                    s.prt(f'Succeed in Stopping the iSCSILogicalUnit resource "{res_name}"', 2)
                    return True
                else:
                    s.pwce('Failed to stop CRM resource ,exit the program...', 3, 2)
            else:
                s.pwce('Failed to stop CRM resource', 3, 2)
        else:
            s.handle_exception()

    def _del_cof(self, res_name):
        '''
        Delete the iSCSILogicalUnit resource
        '''
        unique_str = 'EsTyUqIb5'
        crm_del_cmd = f'crm cof delete {res_name}'
        oprt_id = s.get_oprt_id()
        del_result = s.get_ssh_cmd(SSH, unique_str, crm_del_cmd, oprt_id)
        # a:delete_result为error
        if del_result:
            re_delstr = 'deleted'
            re_result = s.re_findall(
                re_delstr, del_result['rst'].decode('utf-8'))
            if len(re_result)==3:
                s.prt(f'Succeed in deleting the iSCSILogicalUnit resource "{res_name}"', 2)
                return True
            else:
                s.pwce(f'Failed to delete the iSCSILogicalUnit resource "{res_name}"', 3, 2)
        else:
            s.handle_exception()

    def _del(self, res_name):
        s.pwl(f'Deleting crm resource {res_name}',1)
        if self._stop(res_name):
            if self._del_cof(res_name):
                return True

    def get_all_cfgd_res(self):
        # get list of all configured crm res
        cmd_crm_res_show = 'crm res show'
        show_result = s.get_ssh_cmd(
            SSH, 'IpJhGfVc4', cmd_crm_res_show, s.get_oprt_id())
        if show_result['sts']:
            re_crm_res = f'res_\w*_[0-9]{{1,3}}'
            show_result = show_result['rst'].decode('utf-8')
            crm_res_cfgd_list = s.re_findall(re_crm_res, show_result)
            return crm_res_cfgd_list

    def del_crms(self, crm_to_del_list):
        if crm_to_del_list:
            s.pwl('Start to delete CRM resource',0)
            for res_name in crm_to_del_list:
                self._del(res_name)

    def vplx_rescan_r(self):
        '''
        vplx rescan after delete
        '''
        s.scsi_rescan(SSH, 'r')
    
    def _modify_allow_initiator(self):
        iqn_string=' '.join(consts.glo_iqn_list())
        cmd=f'crm conf set {self.lu_name}.allowed_initiators "{iqn_string}"'
        oprt_id=s.get_oprt_id()
        result=s.get_ssh_cmd(SSH,'',cmd,oprt_id)
        if result:
            if result['sts']:
                return True 
            else:
                s.pwe('Failed in modify the allow initiator', 2, 2)
        else:
            s.handle_exception()
    
    def _targetcli_verify(self):
        cmd=f'targetcli ls iscsi/{TARGET_IQN}/tpg1/acls'
        oprt_id=s.get_oprt_id()
        results=s.get_ssh_cmd(SSH,'',cmd,oprt_id)
        if results:
            if results['sts']:
                restr = re.compile(f'''(iqn.1993-08.org.debian:01:2b129695b8bbmaxhost:{self.id}-\d+).*?mapped_lun{self.id}''', re.DOTALL)
                re_result=restr.findall(results['rst'].decode('utf-8'))
                if re_result:
                    if re_result==consts.glo_iqn_list():
                        return True
        else:
            s.handle_exception()

    def _cyclic_check_crm_start(self, res_name, sec, num):
        n = 0
        while n < num:
            n += 1
            if self._get_crm_status(res_name)['status'] =='Stopped':
                time.sleep(sec)
            elif self._get_crm_status(res_name)['status']=='FAILED':
                s.pwe('Failed in CRM status is "FAILED"',2,2)
            else:
                if self._targetcli_verify():
                    return True
    
    def _crm_and_targetcli_verify(self):
        oprt_id=s.get_oprt_id()
        if self._cyclic_check_crm_start(self.lu_name,6,200):
            s.pwl('Success in modify the allow initiator', 2, oprt_id)
        else:
            s.pwe('Failed in verify the allow initiator', 2, 2)  
        


if __name__ == '__main__':
   pass
