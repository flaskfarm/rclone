from support import SupportFile, SupportSubprocess
from support.expand.rclone import SupportRclone
from tool import ToolModalCommand, ToolUtil

from .setup import *

name = 'config'

class ModuleConfig(PluginModuleBase):
    WEB_FOLDERPATH = os.path.join(F.config['path_data'], 'rclone_web')
    WEB_CALL_ID = 'rclone_web_main'

    def __init__(self, P):
        super(ModuleConfig, self).__init__(P, 'setting')
        self.name = name
        self.db_default = {
            f"{self.name}_db_version": "1",
            f"rclone_path": "rclone",
            f"rclone_config_path": os.path.join(F.config['path_data'], 'db', 'rclone.conf'),

            f"web_user" : "admin",
            f"web_pass" : "admin",
            f"web_port" : "5572",
            f"web_auto_start" : "False",
        }
        

    def process_menu(self, page_name, req):
        arg = P.ModelSetting.to_dict()
        if page_name == 'setting':
            arg['path_data'] = F.config['path_data']
            arg['config_abspath'] = ToolUtil.make_path(P.ModelSetting.get('rclone_config_path'))
        elif page_name == 'web':
            arg['is_web_install'] = os.path.exists(self.WEB_FOLDERPATH)
            arg['is_web_running'] = (SupportSubprocess.get_instance_by_call_id(self.WEB_CALL_ID) != None)

        return render_template(f'{P.package_name}_{name}_{page_name}.html', arg=arg)


    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'rclone_version':
            ret['modal'] = SupportRclone.get_version(rclone_path=arg1)
            if ret['modal'] == None:
                ret['ret'] = 'warning'
                ret['msg'] = '버전 확인 실패'
            ret['title'] = 'Rclone 버전'
        elif command == 'rclone_config':
            cmd = [arg1, '--config', arg2, 'config']
            ToolModalCommand.start("rclone config", [cmd])
        elif command == 'config_list':
            ret['data'] = SupportRclone.config_list()
        elif command == 'web_start':
            self.web_start()
            ret['msg'] = '실행하였습니다.'
        elif command == 'web_stop':
            process = SupportSubprocess.get_instance_by_call_id(self.WEB_CALL_ID)
            process.process_close()
            ret['msg'] = '중지하였습니다.'
        elif command == 'web_install':
            def func():
                url = 'https://github.com/rclone/rclone-webui-react/releases/download/v2.0.5/currentbuild.zip'

                ToolModalCommand.start("Rclone WEB 설치",
                    [
                        ['msg', '설치를 시작합니다.'],
                        
                    ]
                )
                ToolModalCommand.send_message(f"다운로드중 : {url}")

                zip_filepath = os.path.join(F.config['path_data'], 'tmp', 'r.zip')
                extract_filepath = os.path.join(F.config['path_data'], 'tmp', 'rclone_web')
                SupportFile.download_file(url, zip_filepath)
                ToolModalCommand.send_message("다운로드 완료")
                ToolModalCommand.send_message("압축 해제중")

                SupportFile.unzip(zip_filepath, extract_filepath)
                target_folderpath = os.path.join(F.config['path_data'], 'rclone_web')
                if os.path.exists(target_folderpath):
                    shutil.rmtree(target_folderpath)
                
                shutil.move(os.path.join(extract_filepath, 'build'), target_folderpath)
                try:
                    import static_host
                except:
                    ToolModalCommand.send_message("정적 호스트 플러그인을 설치한 후 다시 시도하세요.")
                    return
                
                PP = F.PluginManager.get_plugin_instance('static_host')
                if PP == None:
                    ToolModalCommand.send_message("정적 호스트 플러그인 로딩 후 다시 시도하세요.")
                    return
                urlpath = '/rclone_web'
                new_rule = {
                    "location_path": urlpath,
                    "www_root": target_folderpath,
                    "host": "",
                    "auth_type": "ff",
                    "creation_date": datetime.now().isoformat(),
                }
                drules = json.loads(PP.ModelSetting.get("rules"))
                drules.update({urlpath: new_rule})
                PP.ModelSetting.set("rules", json.dumps(drules))

                ToolModalCommand.send_message("설치 완료했습니다.\n정적 호스트 플러그인에 처음 등록한 경우 재시작 후 적용됩니다.")

            threading.Timer(0, func).start()
        elif command == 'web_uninstall':
            if os.path.exists(self.WEB_FOLDERPATH) == False:
                ret['ret'] = 'warning'
                ret['msg'] = '폴더 없음'
            else:
                try:
                    shutil.rmtree(self.WEB_FOLDERPATH)
                    ret['msg'] = "삭제하였습니다."
                except Exception as e: 
                    P.logger.error('Exception:%s', e)
                    P.logger.error(traceback.format_exc())    
                    ret['ret'] = 'warning'
                    ret['msg'] = '삭제 실패'
        



        return jsonify(ret)


    def setting_save_after(self, change_list):
        if 'rclone_path' in change_list or 'rclone_config_path' in change_list:
            self.rclone_init()
        
    def plugin_load(self):
        self.rclone_init()
        if P.ModelSetting.get_bool('web_auto_start'):
            self.web_start()

    def rclone_init(self):
        SupportRclone.initialize(P.ModelSetting.get('rclone_path'), ToolUtil.make_path(P.ModelSetting.get('rclone_config_path')))


    def web_start(self):
        cmd = SupportRclone.rclone_cmd() + [
            'rcd', '--rc-web-gui',
            f"--rc-addr=localhost:{P.ModelSetting.get('web_port')}",
            f"--rc-user={P.ModelSetting.get('web_user')}", 
            f"--rc-pass={P.ModelSetting.get('web_pass')}", 
            '--rc-serve', '--rc-allow-origin=*',
            '--rc-web-gui-no-open-browser',
            f"--rc-files={os.path.join(F.config['path_data'], 'rclone_web')}"
        ]
        process = SupportSubprocess(cmd, call_id=self.WEB_CALL_ID)
        process.start(join=False)


    def get_user_command_list(self, data):
        ret = []
        one = ''
        flag = False
        for d in data:
            if d == ' ':
                if flag == False:
                    ret.append(one)
                    one = ''
                    continue
            elif d == '"':
                flag = not flag
                logger.debug(flag)
                continue
            one += d
        ret.append(one)

        return ret 
