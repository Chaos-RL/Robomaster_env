import numpy as np
from enum import Enum

ROBOT_L = 0.8
ROBOT_W = 0.6
ROBOT_H = 0.6

class Armor(Enum):
    FRONT = 0
    LEFT = 1
    BACK = 2
    RIGHT = 3

class Team(Enum):
    RED = 0
    BLUE = 1

class Pose():
    def __init__(self, position=[0,0,0], linear_speed=[0,0], angular_speed=[0]):
        #TODO: A pose class in utils, a pose+vel calss in utils(refer to nav_msgs/Odometry)
        # self.chassis.x = position[0]
        # self.chassis.y = position[1]
        # self.chassis.theta = position[2]
        self.chassis_position = position
        self.speed = linear_speed + angular_speed
        self.length = 600
        self.width = 600
        self.height = 500
        self.gimbal_angle = 0
        self.gimbal_shoot_speed = 0

class Robot_State():
    def __init__(self, team=Team.BLUE, num=0, on=False, alive=False，position=[0,0,0]): # position: (x,y,theta)
        self.on = on      # do we have this robot in our simulator
        self.alive = alive      
        self.team = team
        self.number = num    # 2 robots with num 0/1
        self.health = 2000
        self.bullet = 0
        self.heat = 0
        # self.position = position
        self.can_move = True
        self.cant_move_time = 0 # the beginning time of no moving condition
        self.can_shoot = True
        self.cant_shoot_time = 0
        self.pose = Pose(position=position)


class Robot():
    def __init__(self, team, num=1, on=True, alive=True, position=[0,0,0]):
        self.state = Robot_State(team, num, on, alive, position)
        self.ally_state = Robot_State()

    def kill(self):
        self.state.alive = False
        self.state.health = 0
        self.state.can_move = False
        self.state.can_shoot = False
    
    def add_bullet(self, num=100):
        self.state.bullet += num
        if self.ally_state.alive == True:
            self.ally_state.bullet += num

    def add_health(self, num=200):
        self.state.health += num
        if self.ally_state.alive == True:
            self.ally_state.bullet += num
        

    def shoot(self, velocity):
        if not self.state.can_shoot:
            return False
        self.state.bullet -= 1
        self.state.heat += velocity
        if 25 < velocity < 30:
            self.add_health(-200)
        elif 30 <= velocity <= 35:
            self.add_health(-1000)
        elif velocity > 35:
            self.add_health(-2000)
        if self.ally_state.alive == True:
            self.ally_state.heat += velocity
        # TODO: success rate of shooting considering distance and velocity
        return True
        
    def disable_moving(self, time):
        self.state.can_move = False
        self.state.cant_move_time = time

    def disable_shooting(self, time):
        self.state.can_shoot = False
        self.state.cant_shoot_time = time

    def disdisable_moving(self,):
        self.state.can_move = True
        self.state.cant_move_time = 0

    def disdisable_shooting(self,):
        self.state.can_shoot = True
        self.state.cant_shoot_time = 0

    #def set_pose
