class LoggerPlugin():
    """

    """ 
        
    def setup_logger(self):    
        raise NotImplementedError("SubClass should implement the \"setup_logger\" method")
    
    def update_time_step(self, cycle_step, simulation_step):
        raise NotImplementedError("SubClass should implement the \"update_time_step\"  method")

    def log_simulation_step(self):    
        raise NotImplementedError("SubClass should implement the \"log_simulation_step\"  method")
    
    def stop_logger(self):    
        raise NotImplementedError("SubClass should implement the \"stop_logger\"  method")