import uuid
from collections import OrderedDict

from support.expand.rclone import SupportRclone, SupportSubprocess
from tool import ToolUtil

from .mod_move import ModelRcloneFile, ModelRcloneJob
from .setup import *


class PageMoveStatus(PluginPageBase):
    
    def __init__(self, P, parent):
        super(PageMoveStatus, self).__init__(P, parent, name='status')
        default_route_socketio_page(self)
    
    def process_menu(self, req):
        arg = self.P.ModelSetting.to_dict()
        job_id = req.args.get('job_id')
        if job_id != None:
            arg['start_job_id'] = job_id
        return render_template(f'{self.P.package_name}_{self.parent.name}_{self.name}.html', arg=arg)


    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'current_status':
            self.send_callback()
        elif command == 'process_stop':
            ret = self.get_page('job').process_stop(arg1)
        return jsonify(ret)


    TRANS_REGEX = {
        'STATUS' : re.compile(r'Transferred\:\s*(?P<trans_data_current>\d.*?)\s\/\s(?P<trans_total_size>\d.*?)\,\s*((?P<trans_percent>\d+)\%)?\-?\,\s*(?P<trans_speed>\d.*?)\,\sETA\s(((?P<rt_hour>\d+)h)*((?P<rt_min>\d+)m)*((?P<rt_sec>.*?)s)*)?\-?'),
        'STATUS_FILECOUNT' : re.compile(r'Transferred\:\s*(?P<file_1>\d+)\s\/\s(?P<file_2>\d+)\,\s*((?P<file_percent>\d+)\%)?\-?'),
        'TIME' : re.compile(r'Elapsed\stime\:\s*((?P<r_hour>\d+)h)*((?P<r_min>\d+)m)*((?P<r_sec>.*?)s)*'),
        'CURRENT_FILE_STATUS' : re.compile(r'\s*\*\s((?P<folder>.*)\/)?(?P<name>.*?)\:\s*(?P<percent>\d+)\%\s*\/(?P<size>\d.*?)\,\s*(?P<speed>\d.*?)\,\s*((?P<rt_hour>\d+)h)*((?P<rt_min>\d+)m)*((?P<rt_sec>.*?)s)*'), 
        'ERROR' : re.compile(r'Errors\:\s*(?P<error>\d+)'),
        'CHECKS' : re.compile(r'Checks\:\s*(?P<check_1>\d+)\s\/\s(?P<check_2>\d+)\,\s*(?P<check_percent>\d+)?\-?'),
        'FILE_FINISH' : re.compile(r'INFO\s*\:\s*((?P<folder>.*)\/)?(?P<name>.*?)\:\s*(?P<status>.*)'),
        #'ERROR_LOG1': re.compile(r'(.*?)ERROR\s:\s(?P<error>.*?)$'),
        #'ERROR_LOG2': re.compile(r'(.*?)Falied\s:\s(?P<error>.*?)$'),
    }

    current_status = OrderedDict()
    
    def stdout_callback(self, call_id, mode, line):
        try:  
            ts = None
            #P.logger.debug(f"{call_id} {mode} {line}")
            job_id = int(call_id.split('_')[-1])
            
            if mode == 'START':
                self.current_status[str(job_id)] = TransStatus(job_id)
                self.current_status['LAST'] = str(job_id)
                self.send_callback('job')
                return
            
            ts = self.current_status.get(str(job_id))

            if mode == 'END':
                ts.set_finish()
                self.send_callback('job')

                job = ModelRcloneJob.get_by_id(job_id)
                job.last_run_time = datetime.now()
                #job.last_file_count = len(ts.file_ids)
                job.last_file_count = ts.file_count
                job.save()

                if job.system_command_id_after != '':
                    ToolUtil.run_system_command_by_id(job.system_command_id_after).join()
                return
            
            if mode != 'LOG' or ts == None or line == None:
                return
            if line == '' or  line.startswith('Checking'):
                return
            if line.endswith('INFO  :'):
                return
            if line.startswith('Deleted:'):
                return
            if line.startswith('Transferring:'):
                return
            if line.startswith('Renamed:'):
                return
            
            is_matched = False
            match = self.TRANS_REGEX["STATUS"].search(line)
            if match:
                is_matched = True
                ts.trans_data_current = match.group('trans_data_current')
                ts.trans_total_size = match.group('trans_total_size')
                ts.trans_percent = match.group('trans_percent')
                ts.trans_speed = match.group('trans_speed')
                ts.rt_hour = match.group('rt_hour')
                ts.rt_min = match.group('rt_min')
                ts.rt_sec = match.group('rt_sec')
             

            match = self.TRANS_REGEX['ERROR'].search(line)
            if match:
                is_matched = True
                ts.error = match.group('error')

            match = self.TRANS_REGEX['CHECKS'].search(line)
            if match:
                is_matched = True
                ts.check_1 = match.group('check_1')
                ts.check_2 = match.group('check_2')
                ts.check_percent = match.group('check_percent')
                return

            match = self.TRANS_REGEX['STATUS_FILECOUNT'].search(line)
            if match:
                is_matched = True
                ts.file_1 = match.group('file_1')
                ts.file_2 = match.group('file_2')
                ts.file_percent = match.group('file_percent')

            match = self.TRANS_REGEX['TIME'].search(line)
            if match:
                is_matched = True
                ts.r_hour = match.group('r_hour')
                ts.r_min = match.group('r_min')
                ts.r_sec = match.group('r_sec')
           
            match = self.TRANS_REGEX['CURRENT_FILE_STATUS'].search(line)
            if match:
                is_matched = True
                #Logic.set_file(match)
                folder = match.groupdict().get('folder')
                name = match.group('name')
                db_file = ModelRcloneFile.get(job_id, folder, name, ts.uuid)
                #P.logger.error(db_file)
                if db_file is None:
                    db_file = ModelRcloneFile(job_id, folder, name, ts.uuid)
                    db_file.save()
                    #if db_file.id not in ts.files:
                    # 2022-12-16
                    if P.ModelSetting.get_bool('move_setting_status_show_filelist'):
                        ts.file_ids.append(db_file.id)
                    ts.file_count += 1

                db_file.percent = int(match.group('percent'))
                db_file.size = match.group('size')
                db_file.speed = match.group('speed')
                db_file.rt_hour = match.group('rt_hour')
                db_file.rt_min = match.group('rt_min')
                db_file.rt_sec = match.group('rt_sec')
                db_file.save()
              
            match = self.TRANS_REGEX['FILE_FINISH'].search(line)
            if match:
                is_matched = True
                folder = match.groupdict().get('folder')
                name = match.group('name')
                db_file = ModelRcloneFile.get(job_id, folder, name, ts.uuid)
                if db_file != None:
                    db_file.set_finish()

            if is_matched == False:
                ts.log.append(line)

            self.send_callback()

        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())   
            P.logger.error(f"[{call_id}] [{mode}] [{data}]")
        finally:

            pass

    def send_callback(self, mode='status'):
        for key, value in self.current_status.items():
            if key == 'LAST':
                continue
            value.files = []
            for db_id in value.file_ids:
                value.files.append(ModelRcloneFile.get_by_id(db_id).as_dict())
        self.socketio_callback(mode, self.current_status)

    def get_current_dict(self):
        ret = []
        for key, value in self.current_status.items():
            data = value.__dict__
            data['files'] = []
            for f in value.files:
                data['files'].append(f.as_dict())
            ret.append(data)
        return ret

    

import json_fix


class TransStatus(object):
    def __init__(self, job_id):
        self.job_id = job_id
        self.trans_data_current = ""
        self.trans_total_size = ""
        self.trans_percent = ""
        self.trans_speed = ""
        self.rt_hour = self.rt_min = self.rt_sec = ""
        self.error = ""
        self.check_1 = ""
        self.check_2 = ""
        self.check_percent = ""
        self.file_1 = ""
        self.file_2 = ""
        self.file_percent = ""
        self.r_hour = self.r_min = self.r_sec = ""
        self.file_ids = []
        self.created_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log = []
        self.job_data = ModelRcloneJob.get_by_id(self.job_id).as_dict()
        self.uuid = str(uuid.uuid4())
        self.files = None
        self.completed_time = None
        self.is_completed = False
        self.file_count = 0

    def set_finish(self):
        self.completed_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.is_completed = True

    def __json__(self):
        return self.__dict__

