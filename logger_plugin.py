class LoggerPlugin():
    """

    """ 
    def load_to_enviroment(self, env):
        raise NotImplementedError("SubClass should implement the \"load_to_enviroment\" method", type(self))

    def start_logger(self):    
        raise NotImplementedError("SubClass should implement the \"setup_logger\" method", type(self))
    
    def update_time_step(self, cycle_step, simulation_step):
        raise NotImplementedError("SubClass should implement the \"update_time_step\"  method", type(self))

    def log_simulation_step(self):    
        raise NotImplementedError("SubClass should implement the \"log_simulation_step\"  method", type(self))
    
    def stop_logger(self):    
        raise NotImplementedError("SubClass should implement the \"stop_logger\"  method", type(self))