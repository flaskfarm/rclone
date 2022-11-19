import imp
import sys

from support import SupportSubprocess, SupportYaml
from support.expand.rclone import SupportRclone
from tool import ToolUtil

from .mod_move import ModelRcloneJob
from .setup import *


class PageMoveJob(PluginPageBase):
    __OPTION_STATIC = '--log-level INFO --stats 1s --stats-file-name-length 0'

    def __init__(self, P, parent):
        super(PageMoveJob, self).__init__(P, parent, name='job')
  

    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'config_list':
            ret['data'] = {}
            ret['data']['remote_list'] = SupportRclone.config_list()
            ret['data']['default'] = P.ModelSetting.to_dict()
            ret['data']['job_list'] = ModelRcloneJob.get_list()
        elif command == 'job_save':
            P.logger.warning(arg1)
            arg_dict = self.arg_to_dict(arg1)
            ret = ModelRcloneJob.update(arg_dict)
            if int(arg_dict['id']) != -1:
                db_item = ModelRcloneJob.get_by_id(arg_dict['id'])
                if db_item.schedule_mode != 'scheduler':
                    F.scheduler.remove_job(f"rclone_move_{arg_dict['id']}")
        elif command == 'job_delete':
            if ModelRcloneJob.delete_by_id(arg1):
                ret['msg'] = "삭제하였습니다."
            else:
                ret['ret'] = 'warning'
                ret['msg'] = "삭제 실패"
        elif command == 'ls':
            ret = self.get_module('config').remote_ls(arg1)
        elif command == 'execute':
            #db_item = ModelRcloneJob.get_by_id(arg1)
            call_id = f"rclone_move_{arg1}"
            process = SupportSubprocess.get_instance_by_call_id(call_id)
            if process != None:
                ret['msg'] = "실행중입니다."
                ret['ret'] = 'warning'
            else:
                self.execute(arg1, False)

        elif command == 'task_sched':
            job_id = arg1
            flag = (arg2 == 'true')
            scheduler_id = f'rclone_move_{job_id}'
            if flag and F.scheduler.is_include(scheduler_id):
                ret['msg'] = '이미 스케쥴러에 등록되어 있습니다.'
            elif flag and F.scheduler.is_include(scheduler_id) == False:
                result = self.__sched_add(job_id)
                ret['msg'] = '스케쥴러에 추가하였습니다.'
            elif flag == False and scheduler.is_include(scheduler_id):
                result = scheduler.remove_job(scheduler_id)
                ret['msg'] = '스케쥴링 취소'
            elif flag == False and scheduler.is_include(scheduler_id) == False:
                ret['msg'] = '등록되어 있지 않습니다.'
        elif command == 'process_stop':
            ret = self.process_stop(arg1)
        return jsonify(ret)


    def plugin_load(self):
        def func():
            try:
                db_items = ModelRcloneJob.get_list()
                for db_item in db_items:
                    if db_item['schedule_mode'] == 'startup':
                        th = threading.Thread(target=self.execute, args=(db_item['id'], True))
                        th.setDaemon(True)
                        th.start()
                    elif db_item['schedule_mode'] == 'scheduler' and db_item['schedule_auto_start']:
                        self.__sched_add(db_item['id'])
            except Exception as e: 
                logger.error(f"Exception:{str(e)}")
                logger.error(traceback.format_exc())        
        try:
            th = threading.Thread(target=func)
            th.setDaemon(True)
            th.start()
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())   



    def __sched_add(self, id, db_item=None):
        try:
            if db_item is None:
                db_item = ModelRcloneJob.get_by_id(id)
            job_id = f"rclone_move_{db_item.id}"
            if scheduler.is_include(job_id):
                return
            job = Job(self.P.package_name, job_id, db_item.schedule_interval, self.execute, db_item.description,  args=(db_item.id, True))
            scheduler.add_job_instance(job)
            return True
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())   
        return False


    def execute(self, *args, **kwargs):
        try:
            #P.logger.error(args)
            #P.logger.error(kwargs)
            db_id = args[0]
            db_item = ModelRcloneJob.get_by_id(db_id)

            if db_item.system_command_id_before != '':
                ToolUtil.run_system_command_by_id(db_item.system_command_id_before).join()

            cmd = SupportRclone.rclone_cmd() + [
                db_item.command,
                self.change_path(db_item.source_path),
                self.change_path(db_item.target_path),
            ]
            cmd += self.__OPTION_STATIC.split(' ')
            cmd += self.get_module('config').get_user_command_list(db_item.option_user)
            #P.logger.info(d(cmd))
            db_item.process_command = ' '.join(cmd)
            db_item.save()
            process = SupportSubprocess(cmd, call_id=f"rclone_move_{db_id}", stdout_callback=self.get_page('status').stdout_callback)
            process.start(join=args[1])
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())   


    def process_stop(self, db_id):
        ret = {}
        call_id = f"rclone_move_{db_id}"
        process = SupportSubprocess.get_instance_by_call_id(call_id)
        if process == None:
            ret['msg'] = "실행중이 아닙니다."
            ret['ret'] = 'warning'
        else:
            process.process_close()
            ret['msg'] = "중지하였습니다."
            ret['ret'] = 'success'
        return ret


    def change_path(self, src):
        yaml_path = os.path.join(F.config['path_data'], 'db', 'rclone.yaml')
        if os.path.exists(yaml_path):
            data = SupportYaml.read_yaml(yaml_path)

            if data.get('folder_change_rule', None) != None:
                for item in data['folder_change_rule']:
                    if item['target'] in src:
                        try:
                            mod = imp.new_module('rclone_change_rule')
                            exec(item['code'], mod.__dict__)
                            P.logger.info(f"{item['target']} {mod.RESULT}")
                            src = src.replace(item['target'], mod.RESULT)
                        except Exception as e: 
                            P.logger.error(f'Exception:{str(e)}')
                            P.logger.error(traceback.format_exc())

        now = datetime.now()
        return src.replace('{DATETIME}', now.strftime('%Y%m%d_%H%M%S')) \
            .replace('{DATE}', now.strftime('%Y-%m-%d')) \
            .replace('{TIME}', now.strftime('%H%M%S'))

    
    


