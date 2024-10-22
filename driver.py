import muse


class DisplayDriver():

    def __init__(self):
        self.is_powered = False
        self.pic_is_muted = False
        
    def update_state(self, feedback):
        pass

    def toggle_power(self):
        pass

    def power_on():
        pass

    def power_off():
        pass

    def toggle_pic_mute():
        pass


class LGDriver(DisplayDriver):

    #commands
    POWER_OFF_COMMAND = 'ka 00 00\x0D'
    POWER_ON_COMMAND = 'ka 00 01\x0D'
    PIC_MUTE_OFF_COMMAND = 'kd 0 00\x0D'
    PIC_MUTE_ON_COMMAND = 'kd 1 01'
    #acknowledgements
    POWER_ON_ACK = 'a 01 OK01x\x0D'
    POWER_OFF_ACK = 'a 01 OK00x\x0D'
    PIC_MUTE_ON_ACK = 'd 01 OK01x\x0D'
    PIC_MUTE_OFF_ACK = 'd 01 OK00x\x0D'

    def __init__(self,device):
        super.__init__()
        self.device =  device

    def update_state(self, cls, feedback):
        lines = feedback.split("\x0D")
        for line in lines:
            match line:
                case cls.POWER_OFF_ACK: self.is_powered = False
                case cls.POWER_ON_ACK: self.is_powered = True
                case cls.PIC_MUTE_OFF_ACK: self.pic_is_muted = False
                case cls.PIC_MUTE_ON_ACK: self.pic_is_muted = True 
        
    def toggle_power(self):
        if self.is_powered:
            self.device.send(self.POWER_OFF_COMMAND)
        else:
            self.device.send(self.POWER_ON_COMMAND)

    def power_off(self):
        self.device.send(self.POWER_OFF_COMMAND)
  
    def power_on(self):
        self.device.send(self.POWER_ON_COMMAND)
   
    def toggle_pic_mute(self):
        if self.pic_is_muted:
            return self.PIC_MUTE_OFF_COMMAND
        else:
            return self.PIC_MUTE_ON_COMMAND