from support import SupportSubprocess
from support.expand.rclone import SupportRclone

from .setup import *

name = 'serve'

class ModuleServe(PluginModuleBase):
    DEFAULT_OPTION = "--addr=localhost:8080 --user=admin --pass=admin --poll-interval=1m --buffer-size=32M --vfs-read-chunk-size=32M --vfs-read-chunk-size-limit=2048M --vfs-cache-mode=full --dir-cache-time=1m --vfs-cache-max-size=30G" 

    def __init__(self, P):
        super(ModuleServe, self).__init__(P, 'setting')
        self.name = name
        self.db_default = {
            f'{self.name}_db_version': '1',
        }

    def process_menu(self, page_name, req):
        arg = P.ModelSetting.to_dict()
        return render_template(f'{P.package_name}_{name}_{page_name}.html', arg=arg)
    
    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'serve_save':
            arg_dict = self.arg_to_dict(arg1)
            ret = ModelRcloneServe.update(arg_dict)
        elif command == 'serve_list':
            ret['data'] = {}
            ret['data']['remote_list'] = SupportRclone.config_list()
            ret['data']['default'] = self.DEFAULT_OPTION
            ret['data']['serve_list'] = ModelRcloneServe.get_list(by_dict=True)
            for item in ret['data']['serve_list']:
                item['process'] = (self.process_check(item) != None)
        elif command == 'ls':
            ret = self.get_module('config').remote_ls(arg1)
        elif command == 'serve_delete':
            if ModelRcloneServe.delete_by_id(arg1):
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
            db_item = ModelRcloneServe.get_by_id(db_id)
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
                    if 'serve' in cmd and db_item['remote_path'] in cmd and db_item['protocol'] in cmd:
                        return process
                except:
                    pass
        except:
            pass

    def execute(self, *args, **kwargs):
        try:
            db_id = args[0]
            db_item = ModelRcloneServe.get_by_id(db_id)
            if db_item.cache_dir == '':
                return {'ret':'warning', 'msg':'캐시 정보 없음.'}
            db_item = ModelRcloneServe.get_by_id(db_id)
            logfile = os.path.join(F.config['path_data'], 'log', f"rclone_serve_{db_id}.log")
            process = self.process_check(db_item.as_dict())
            if process != None:
                return {'ret':'warning', 'msg':'실행중인 프로세스가 있습니다.'}

            cmd = SupportRclone.rclone_cmd() + [
                'serve',
                db_item.protocol,
                db_item.remote_path,
                "--log-level=INFO", 
                f"--log-file={logfile}", 
                f"--cache-dir={db_item.cache_dir}"
            ]
            P.logger.info(' '.join(cmd))
            cmd += self.get_module('config').get_user_command_list(db_item.option)
            
            process = SupportSubprocess(cmd, call_id=f"rclone_serve_{db_id}")
            process.start(join=False)
            SupportSubprocess.remove_instance(process)
            return {'ret':'success', 'msg':'실행하였습니다.'}
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())   


    def plugin_load(self):
        items = ModelRcloneServe.get_list(by_dict=True)
        for item in items:
            if item['start_mode'] == 'all':
                th = threading.Thread(target=self.execute, args=(item['id'],))
                th.setDaemon(True)
                th.start()
    
    def plugin_unload(self):
        items = ModelRcloneServe.get_list(by_dict=True)
        for item in items:
            if item['finish_mode'] == 'all':
                th = threading.Thread(target=self.process_stop, args=(item['id'],))
                th.setDaemon(True)
                th.start()







class ModelRcloneServe(ModelBase):
    P = P
    __tablename__ = f'{P.package_name}_serve'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time = db.Column(db.DateTime)
    name = db.Column(db.String)
    protocol = db.Column(db.String)
    remote_path = db.Column(db.String)
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
                db_item = ModelRcloneServe()
                db_item.save()
            else:
                db_item = cls.get_by_id(data['id'])
            db_item.protocol = data['serve_protocol']
            db_item.remote_path = data['serve_remote_path']
            db_item.option = data['serve_option']
            db_item.start_mode = data['serve_start_mode']
            db_item.finish_mode = data['serve_finish_mode']
            db_item.cache_dir = data['serve_cache_dir']
            if data['serve_name'] == '':
                db_item.name = db_item.id
            else:
                db_item.name = data['serve_name']
            db_item.save()
            ret['ret'] = 'success'
            ret['msg'] = '업데이트 하였습니다.'
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
            ret['ret'] = 'warning'
            ret['msg'] = '실패'
        return ret

