#!/usr/bin/env python
import threading
from enum import Enum
import map
from robot import Armor, Team, RobotState, Robot, Pose
import time
# from geometry_msgs.msg import Pose, Twist, Point
# from nav_msgs.msg import Odometry
from roborts_msgs.msg import env_input, env_output, vel_command_stack, output_to_gazebo, vel_command_stack

DURATION = 180 # length of a game
FREQUENCY = 10

def thread_job():
    rospy.spin()

class RMAI_GAME():
    def __init__(self):
        self.duration = DURATION
        self.start_time = time.time()
        self.passed_time = 0
        self.map = map.RM_map()
        self.reset()
        self.red_alive = True
        self.blue_alive = True

        # I trylly prefer to use dict
        self.robots = { ("RED", 0): Robot(Team.RED, id=0), 
                        ("RED", 1): Robot(Team.RED, id=1), 
                        ("BLUE", 0): Robot(Team.BLUE, id=0), 
                        ("BLUE", 1): Robot(Team.BLUE, id=1)]
        
        # set initial position in boot areas

        for i, j in enumerate(self.robots):
            boot = self.map.bootareas[i]
            self.robots[j].state.pose = Pose(position=[(boot.x[0] + boot.x[1]) / 2, (boot.y[0] + boot.y[1]) / 2, 0])
        
        self.robots[('BLUE', 0)].ally = self.robots[('BLUE', 1)]
        self.robots[('BLUE', 1)].ally = self.robots[('BLUE', 0)]
        self.robots[('RED', 0)].ally = self.robots[('RED', 1)]
        self.robots[('RED', 1)].ally = self.robots[('RED', 0)]

        self.robots[('BLUE', 0)].enemies.append(self.robots[('RED', 0)])
        self.robots[('BLUE', 0)].enemies.append(self.robots[('RED', 1)])
        self.robots[('BLUE', 1)].enemies.append(self.robots[('RED', 0)])
        self.robots[('BLUE', 1)].enemies.append(self.robots[('RED', 1)])
        self.robots[('RED', 0)].enemies.append(self.robots[('BLUE', 0)])
        self.robots[('RED', 0)].enemies.append(self.robots[('BLUE', 1)])
        self.robots[('RED', 1)].enemies.append(self.robots[('BLUE', 0)])
        self.robots[('RED', 1)].enemies.append(self.robots[('BLUE', 1)])

        rospy.init_node('gym_env', anonymous=True)

        rospy.Subscriber("/Topic_param1", env_input, self.gazebo_callback, tcp_nodelay=True)
        # command input, shooting command needed
        rospy.Subscriber("/Topic_param2", vel_command_stack, self.vel_command_callback, tcp_nodelay=True)

        # to user
        self.info_pub = rospy.Publisher('/Topic_param3', env_output, queue_size=10)
        # to gazebo, robot alive or not, can move or not
        self.condition_pub = rospy.Publisher('/Topic_param4', output_to_gazebo, queue_size=10)

        add_thread = threading.Thread(target = thread_job)
        add_stread.start()

    def step(self, linear_speeds, angular_speeds, gimbal_speeds, shoot_commands):# default order: red0,red1,blue0,blue1
        '''
        linear_speeds: linear speed of 4 robots' chassis, default = 0
        angular_speeds: angular_speeds speed of 4 robots' chassis, default = 0
        gimbal_speeds: angular_speeds speed of 4 robots' gimbal, default = 0
        shoot_commands: [{'taget':i，'armor':j,'shooting_direction':0-360,'laser_direction':0-360,'velocity':num},{},{},{}]  shooting commands of 4 robots, containing shooting direction(0-360), default = -100 means no shooting
        '''
        # 1. send velocities to physical simulator

        # 2. update everything (using gazebo callback)


        # 3. reset map if needed
        self.passed_time = time.time()-self.start_time
        if self.passed_time // 60 == 1 or 2:
            self.map.randomlize()
        
        # 4. step robot
        self.red_alive = False
        self.blue_alive = False

        for i, idx in enumerate(self.robots):

            robo = self.robots[idx]

            # 4.0 survival state
            if robo.state.alive == False:
                continue
            elif idx[0] == 'BLUE':
                self.blue_alive = True
            else:
                self.red_alive = True
            # # 4.0 position update, done in callback
            # robo.state.pose.chassis_position = position[i]

            # 4.1 funcional areas
            for f in self.map.fareas:
                if f.inside(robo.state.pose.x, robo.state.pose.y):
                    if f.type == map.Region.FREE:
                        pass
                    elif f.type == map.Region.REDBULLET:
                        self.robots[('RED', 0)].add_bullet()
                        f.set_type(map.Region.FREE)
                    elif f.type == map.Region.BLUEBULLET:
                        self.robots[('BLUE', 0)].add_bullet()
                        f.set_type(map.Region.FREE)
                    elif f.type == map.Region.REDHEALTH:
                        self.robots[('RED', 0)].add_health()
                        f.set_type(map.Region.FREE)
                    elif f.type == map.Region.BLUEHEALTH:
                        self.robots[('BLUE', 0)].add_health()
                        f.set_type(map.Region.FREE)
                    elif f.type == map.Region.NOMOVING:
                        robo.disable_moving(time.time())
                        f.set_type(map.Region.FREE)
                    else:
                        robo.disable_shooting(time.time())
                        f.set_type(map.Region.FREE) 

                    break   
            
            # 4.2 punish state update
            if not robo.state.can_move:
                if (time.time() - robo.state.cant_move_time) > 10:
                    robo.disdisable_moving()
            if not robo.state.can_shoot:
                if (self.time - robo.state.cant_shoot_time) > 10:
                    robo.disdisable_shooting()

            # 4.3 shooting, TODO:
            if robo.shoot(shoot_commands[i]['velocity']):
                if abs(shoot_commands[i]['shooting_direction']-shoot_commands[i]['laser_direction']) < 20:
                    self.robots[shoot_commands[i]['taget']].add_health(shoot_commands[i]['armor'] * 20)
            
            # 4.4 health update
              # 4.4.1 heating damage
            if robo.state.heat > 240:
                robo.add_health(-(robo.state.heat - 240) * 4 ) 
            elif robo.state.heat > 360:
                robo.add_health(-(robo.state.heat - 360) * 40) 
                robo.state.heat = 360
            
            # 4.5 kill dead robot
            if robo.state.health <= 0:
                robo.kill()
                
            # 4.6 heat cooldown
            cooldown_value = 240 if robo.state.health < 400 else 120
            robo.state.heat = robo.state.heat > cooldown_value / FREQUENCY and robo.state.heat - cooldown_value / FREQUENCY or 0
            
        done = self.done()
        # ignore: collision punishment
        return done

    def done(self):
        if self.passed_time >= DURATION:
            return True

        if (not self.red_alive) or not (self.blue_alive):
            return True 

    def reset(self):
        self.time = 0
        self.passed_time = 0
        self.map.reset()
        self.robots = { ("RED", 0): Robot(Team.RED, num=0), 
                ("RED", 1): Robot(Team.RED, num=1), 
                ("BLUE", 0): Robot(Team.BLUE, num=0), 
                ("BLUE", 1): Robot(Team.BLUE, num=1)]
        
        # set initial position in boot areas

        for i, j in enumerate(self.robots):
            boot = self.map.bootareas[i]
            self.robots[j].state.pose = Pose(position=[(boot.x[0] + boot.x[1]) / 2, (boot.y[0] + boot.y[1]) / 2, 0])
        
        self.robots[('BLUE', 0)].ally = self.robots[('BLUE', 1)]
        self.robots[('BLUE', 1)].ally = self.robots[('BLUE', 0)]
        self.robots[('RED', 0)].ally = self.robots[('RED', 1)]
        self.robots[('RED', 1)].ally = self.robots[('RED', 0)]

    def gazebo_callback(self, data):
        '''
        update: chassis pose, twist
                gimabal pose, twist
                laser distance
        '''

        for i, msg in enumerate(data):
            header = msg.header.frame_id.split()
            robot_key = (header[0], int(header[1]))
            
            robot = self.robots.get(robot_key, None)
            if robot:
                robot.state.pose.chassis_pose = msg.chassis_odom.pose.pose.position
                robot.state.pose.chassis_speed = msg.chassis_odom.twist.twist
                robot.state.pose.gimbal_pose = msg.gimbal_odom
                robot.state.laser_distance = msg.laser_distance

    def vel_command_callback(self, data):
        '''
        update: shoot command
        '''

        for i, msg in enumerate(data):
            header = msg.header.frame_id.split()
            robot_key = (header[0], int(header[1]))       
            robot = self.robots.get(robot_key, None)

            if robot:
                robot.shoot_command = msg.shoot

    def publish_vel_command(self, data):
        self.condition_pub.publish(data)

    def publish_info(self, data):
        self.info_pub.publish(data)

    def publish_all(self):
        # vel_info = vel_command_stack()
        info = env_output()
        info.map = []
        for i in self.map.fareas:
            info.map.append(Int8((i.type.value - 2)))

        for idx in self.robots:
            robot = self.robots[idx]
            robot_key = idx[0] + ' ' + str(int(idx[1]))

            robot_info = robot_output()
            robot_info.frame_id = robot_key

'''nav_msgs/Odometry chassis_odom
# theta, w, dw
geometry_msgs/Point gimbal_odom

bool alive
bool movable
bool shootable

uint16 health
uint16 bullets
uint16 heat
'''
            robot_info.alive = robot.state.alive
            robot_info.movable = robot.state.can_move
            robot_info.shootable = robot.state.can_shoot

            robot_info.health = robot.state.health
            robot_info.bullets = robot.state.bullet
            robot_info.heat = robot.state.heat


if __name__ == "__main__":
    game = RMAI_GAME()
    epoch = 1 / FREQUENCY
    while not rospy.is_shutdown():
        game.step()
        rospy.sleep(epoch)