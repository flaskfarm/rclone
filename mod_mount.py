from support import SupportSubprocess
from support.expand.rclone import SupportRclone

from .setup import *

name = 'mount'

class ModuleMount(PluginModuleBase):
    DEFAULT_OPTION = "--poll-interval=1m --buffer-size=32M --vfs-read-chunk-size=32M --vfs-read-chunk-size-limit=2048M --vfs-cache-mode=full --dir-cache-time=1m --vfs-cache-max-size=30G" 

    def __init__(self, P):
        super(ModuleMount, self).__init__(P, 'setting')
        self.name = name
        self.db_default = {
            f'{self.name}_db_version': '1',
        }

    def process_menu(self, page_name, req):
        arg = P.ModelSetting.to_dict()
        return render_template(f'{P.package_name}_{name}_{page_name}.html', arg=arg)
    
    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'mount_save':
            arg_dict = self.arg_to_dict(arg1)
            ret = ModelRcloneMount.update(arg_dict)
        elif command == 'mount_list':
            ret['data'] = {}
            ret['data']['remote_list'] = SupportRclone.config_list()
            ret['data']['default'] = self.DEFAULT_OPTION
            ret['data']['mount_list'] = ModelRcloneMount.get_list(by_dict=True)
            for item in ret['data']['mount_list']:
                item['process'] = (self.process_check(item) != None)
        elif command == 'ls':
            tmp = arg1.split(':')
            if len(tmp) == 1:
                if os.path.exists(arg1):
                    ret['modal'] = '\n'.join(os.listdir(arg1))
                    ret['title'] = arg1
                else:
                    ret['ret'] = 'warning'
                    ret['msg'] = 'NOT EXISTS'
            elif len(tmp) == 2:
                lsjson = SupportRclone.lsjson(arg1)
                if lsjson != None:
                    ret['json'] = lsjson
                    ret['title'] = arg1
                else:
                    ret['msg'] = "실패"
                    ret['ret'] = 'warning'
            else:
                ret['ret'] = 'warning'
                ret['msg'] = '실패'
        elif command == 'mount_delete':
            if ModelRcloneMount.delete_by_id(arg1):
                ret['msg'] = "삭제하였습니다."
            else:
                ret['ret'] = 'warning'
                ret['msg'] = "삭제 실패"
        elif command == 'execute':
            ret = self.execute(arg1)
        elif command == 'process_stop':
            ret = self.process_stop(arg1)
        return jsonify(ret) 

    def process_stop(self, *args, **kwargs):
        try:
            db_id = args[0]
            db_item = ModelRcloneMount.get_by_id(db_id)
            process = self.process_check(db_item.as_dict())
            if process == None:
                return {'ret':'warning', 'msg':'실행중인 프로세스가 없습니다.'}
            if process is not None:
                process.kill()
            return {'ret':'success', 'msg':'중지하였습니다.'}
        except Exception as e: 
            logger.error(f'Exception:{str(e)}')
            logger.error(traceback.format_exc())           
        return {'ret':'warning', 'msg':'실패'}

    def process_check(self, db_item):
        try:
            import psutil
            for process in psutil.process_iter():
                try:
                    if process.name().startswith('rclone') == False:
                        continue
                    cmd = process.cmdline()
                    if 'mount' in cmd and db_item['remote_path'] in cmd and db_item['local_path'] in cmd:
                        return process
                except:
                    pass
        except:
            pass

    def execute(self, *args, **kwargs):
        try:
            db_id = args[0]
            db_item = ModelRcloneMount.get_by_id(db_id)
            if db_item.cache_dir == '':
                return {'ret':'warning', 'msg':'캐시 정보 없음.'}
            db_item = ModelRcloneMount.get_by_id(db_id)
            logfile = os.path.join(F.config['path_data'], 'log', f"rclone_mount_{db_id}.log")
            process = self.process_check(db_item.as_dict())
            if process != None:
                return {'ret':'warning', 'msg':'실행중인 프로세스가 있습니다.'}

            cmd = SupportRclone.rclone_cmd() + [
                'mount',
                db_item.remote_path,
                db_item.local_path,
                "--log-level=INFO", 
                f"--log-file={logfile}", 
                f"--cache-dir={db_item.cache_dir}"
            ]
            cmd += self.get_module('config').get_user_command_list(db_item.option)
            P.logger.info(' '.join(cmd))
            process = SupportSubprocess(cmd, call_id=f"rclone_mount_{db_id}")
            process.start(join=False)
            SupportSubprocess.remove_instance(process)
            return {'ret':'success', 'msg':'실행하였습니다.'}
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())   


    def plugin_load(self):
        items = ModelRcloneMount.get_list(by_dict=True)
        for item in items:
            if item['start_mode'] == 'all':
                th = threading.Thread(target=self.execute, args=(item['id'],))
                th.setDaemon(True)
                th.start()
    
    def plugin_unload(self):
        items = ModelRcloneMount.get_list(by_dict=True)
        for item in items:
            if item['finish_mode'] == 'all':
                th = threading.Thread(target=self.process_stop, args=(item['id'],))
                th.setDaemon(True)
                th.start()







class ModelRcloneMount(ModelBase):
    P = P
    __tablename__ = f'{P.package_name}_mount'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)
    name = db.Column(db.String)
    remote_path = db.Column(db.String)
    local_path = db.Column(db.String)
    option = db.Column(db.String)
    start_mode = db.Column(db.String)
    finish_mode = db.Column(db.String)
    cache_dir = db.Column(db.String)

    def __init__(self): 
        self.created_time = datetime.now()

    @classmethod
    def update(cls, data):
        try:
            ret = {}
            if int(data['id']) == -1:
                db_item = ModelRcloneMount()
                db_item.save()
            else:
                db_item = cls.get_by_id(data['id'])
            db_item.remote_path = data['mount_remote_path']
            db_item.local_path = data['mount_local_path']
            db_item.option = data['mount_option']
            db_item.start_mode = data['mount_start_mode']
            db_item.finish_mode = data['mount_finish_mode']
            db_item.cache_dir = data['mount_cache_dir']
            if data['mount_name'] == '':
                db_item.name = db_item.id
            else:
                db_item.name = data['mount_name']
            db_item.save()
            ret['ret'] = 'success'
            ret['msg'] = '업데이트 하였습니다.'
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
            ret['ret'] = 'warning'
            ret['msg'] = '실패'
        return ret

