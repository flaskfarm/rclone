setting = {
    'filepath' : __file__,
    'use_db': True,
    'use_default_setting': True,
    'home_module': None,
    'menu': {
        'uri': __package__,
        'name': 'RCLONE',
        'list': [
            {
                'uri': 'config',
                'name': 'Config',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                    {'uri': 'web', 'name': 'WEB-UI'},
                    {'uri': 'manual/files/config.md', 'name': '매뉴얼'},
                ]
            },
            {
                'uri': 'move',
                'name': 'Move & Copy & Sync',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                    {'uri': 'job', 'name': '작업 목록'},
                    {'uri': 'status', 'name': '작업 상태'},
                    {'uri': 'list', 'name': '작업 결과 목록'},
                    {'uri': 'manual/files/move.md', 'name': '매뉴얼'},
                ]
            },
            {
                'uri': 'mount',
                'name': 'Mount',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                    {'uri': 'manual/files/mount.md', 'name': '매뉴얼'},
                ]
            },
            {
                'uri': 'serve',
                'name': 'Serve',
                'list': [
                    {'uri': 'setting', 'name': '설정'},
                    {'uri': 'manual/files/serve.md', 'name': '매뉴얼'},
                ]
            },
            {
                'uri': 'manual',
                'name': '매뉴얼',
                'list': [
                    {
                        'uri': 'README.md',
                        'name': 'README',
                    },
                ]
            },
            {
                'uri': 'log',
                'name': '로그',
            },
        ]
    },
    'default_route': 'normal',
}
from plugin import *

P = create_plugin_instance(setting)
try:
    from .mod_config import ModuleConfig
    from .mod_mount import ModuleMount
    from .mod_move import ModuleMove
    from .mod_serve import ModuleServe
    P.set_module_list([ModuleConfig, ModuleMove, ModuleMount, ModuleServe])
except Exception as e:
    P.logger.error(f'Exception:{str(e)}')
    P.logger.error(traceback.format_exc())
