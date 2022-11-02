from support import SupportSubprocess

from .setup import *


class ModuleMove(PluginModuleBase):
    
    def __init__(self, P):
        super(ModuleMove, self).__init__(P, name='move', first_menu='status')
        self.db_default = {
            f'{self.name}_db_version': '1',
            f'{P.package_name}_file_last_list_option': "",
        }
        from .page_move_job import PageMoveJob
        from .page_move_status import PageMoveStatus
        self.set_page_list([PageMoveJob, PageMoveStatus, PageMoveSetting, PageMoveList])
        self.web_list_model = ModelRcloneFile
       

class PageMoveSetting(PluginPageBase):
    def __init__(self, P, parent):
        super(PageMoveSetting, self).__init__(P, parent, name='setting')
        self.db_default = {
            'option_move' : '--transfers=4 --checkers=8 --delete-empty-src-dirs --create-empty-src-dirs --delete-after --drive-chunk-size=256M',
            'option_copy' : '--transfers=4 --checkers=8 --create-empty-src-dirs --drive-chunk-size=256M',
            'option_sync' : '--transfers=4 --checkers=8 --create-empty-src-dirs --drive-chunk-size=256M',
        }

class PageMoveList(PluginPageBase):
    
    def __init__(self, P, parent):
        super(PageMoveList, self).__init__(P, parent, name='list')
        

    def process_menu(self, req):
        arg = self.P.ModelSetting.to_dict()
        job_list = ModelRcloneJob.get_list()
        ret = [['all', 'JOB전체']]
        for job in job_list:
            ret.append([job['id'], job['name']])
        arg['job_list'] = ret
        job_id = req.args.get('job_id')
        if job_id != None:
            arg['start_job_id'] = job_id

        return render_template(f'{self.P.package_name}_{self.parent.name}_{self.name}.html', arg=arg)


    def process_command(self, command, arg1, arg2, arg3, req):
        ret = {'ret':'success'}
        if command == 'db_delete':
            if ModelRcloneFile.delete_all(days=arg1):
                ret['msg'] = '삭제하였습니다.'
            else:
                ret['msg'] = '삭제 실패'
                ret['ret'] = 'warning'
        elif command == 'db_delete_item':
            if ModelRcloneFile.delete_by_id(arg1):
                ret['msg'] = '삭제하였습니다.'
            else:
                ret['msg'] = '삭제 실패'
                ret['ret'] = 'warning'
        return jsonify(ret)



























class ModelRcloneJob(ModelBase):
    P = P
    __tablename__ = f'{P.package_name}_job'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time    = db.Column(db.DateTime)
    command = db.Column(db.String)
    name = db.Column(db.String)
    description = db.Column(db.String)
    source_path = db.Column(db.String)
    target_path = db.Column(db.String)
    option_user = db.Column(db.String)
    schedule_mode = db.Column(db.String)
    schedule_interval = db.Column(db.String)
    schedule_auto_start = db.Column(db.Boolean)
    process_command = db.Column(db.String)
    system_command_id_before = db.Column(db.String)
    system_command_id_after = db.Column(db.String)

    last_run_time = db.Column(db.DateTime)
    last_file_count = db.Column(db.Integer)
    def __init__(self):
        self.created_time = datetime.now()
    

    @classmethod
    def update(cls, data):
        try:
            ret = {}
            if int(data['id']) == -1:
                db_item = ModelRcloneJob()
                db_item.save()
            else:
                db_item = cls.get_by_id(data['id'])
            #P.logger.error(db_item)
            db_item.command = data['job_command']
            db_item.source_path = data['job_source_path']
            db_item.target_path = data['job_target_path']
            db_item.option_user = data['job_option_user']
            db_item.system_command_id_before = data['job_system_command_id_before']
            db_item.system_command_id_after = data['job_system_command_id_after']
            db_item.schedule_mode = data['job_schedule_mode']
            db_item.schedule_interval = data['job_schedule_interval']
            db_item.schedule_auto_start = (data['job_schedule_auto_start'] == 'True')

            if data['job_name'] == '':
                db_item.name = db_item.id
            else:
                db_item.name = data['job_name']
            

            if data['job_description'] == '':
                db_item.description = f"Rclone {db_item.command} {db_item.name}"
            else:
                db_item.description = data['job_description']

            db_item.save()

            ret['ret'] = 'success'
            ret['msg'] = '업데이트 하였습니다.'
        except Exception as e: 
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
            ret['ret'] = 'warning'
            ret['msg'] = '실패'
        return ret

    @classmethod
    def get_list(cls):
        ret = super().get_list(by_dict=True)
        for item in ret:
            item['scheduler_is_include'] = F.scheduler.is_include(f"rclone_move_{item['id']}")
            item['scheduler_is_running'] = F.scheduler.is_running(f"rclone_move_{item['id']}")
            item['process'] = (SupportSubprocess.get_instance_by_call_id(f"rclone_move_{item['id']}") != None)
        #P.logger.debug(SupportSubprocess.get_list())
        return ret







class ModelRcloneFile(ModelBase):
    P = P
    __tablename__ = f'{P.package_name}_file'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    created_time    = db.Column(db.DateTime)

    job_id = db.Column(db.Integer)
    folder = db.Column(db.String)
    name = db.Column(db.String)
    percent = db.Column(db.Integer)
    size = db.Column(db.String)
    speed = db.Column(db.String)
    rt_hour = db.Column(db.String)
    rt_min = db.Column(db.String)
    rt_sec = db.Column(db.String)
    log = db.Column(db.String)
    created_time = db.Column(db.DateTime)
    finish_time = db.Column(db.DateTime)
    uuid = db.Column(db.String)

    def __init__(self, job_id, folder, name, uuid): 
        self.job_id = int(job_id)
        self.folder = folder
        self.name = name
        self.uuid = uuid
        self.log = ''
        self.created_time = datetime.now()

    def set_finish(self):
        self.percent = 100
        self.finish_time = datetime.now()
        self.save()

    @classmethod
    def get(cls, job_id, folder, name, uuid):
        try:
            with F.app.app_context():
                #dt = datetime.strptime(timestr, '%Y-%m-%d %H:%M:%S') 
                return F.db.session.query(cls).filter_by(job_id=int(job_id), folder=folder, name=name, uuid=uuid).first()
                #.filter(cls.created_time > dt)
        except Exception as e:
            cls.P.logger.error(f'Exception:{str(e)}')
            cls.P.logger.error(traceback.format_exc())

    # 오버라이딩
    @classmethod
    def make_query(cls, req, order='desc', search='', option1='all', option2='all'):
        with F.app.app_context():
            query = F.db.session.query(cls)
            query1 = cls.make_query_search(F.db.session.query(cls), search, cls.name)

            query2 = cls.make_query_search(F.db.session.query(cls), search, cls.folder)
            query = query1.union(query2)

            if option1 == 'completed':
                query = query.filter(cls.finish_time!=None)
            elif option1 == 'incompleted':
                query = query.filter(cls.finish_time==None)

            if option2 != 'all':
                query = query.filter(cls.job_id==option2)
            if order == 'desc':
                query = query.order_by(desc(cls.id))
            else:
                query = query.order_by(cls.id)
            return query 
