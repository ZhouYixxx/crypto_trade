import common_helper
import dataclass


class GlobalSettings:
    def __init__(self):
        config = common_helper.Util.load_config()
        self.config:dataclass.Config = config
        self.inst_update_dict = common_helper.ImmutableViewDict()

# 创建全局实例
global_instance = GlobalSettings()