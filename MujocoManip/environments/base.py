import numpy as np
from MujocoManip.miscellaneous import SimulationError, XMLError, MujocoPyRenderer
from mujoco_py import MjSim
from collections import OrderedDict
import glfw
from mujoco_py import load_model_from_path, load_model_from_xml

REGISTERED_ENVS = {}

def register_env(target_class):
    REGISTERED_ENVS[target_class.__name__] = target_class

def make(env_name, *args, **kwargs):
    """
        Try to get the equivalent functionality of gym.make in a sloppy way.
    """
    if env_name not in REGISTERED_ENVS:
        raise Exception('Environment {} not found. Make sure it is a registered environment among: {}'.format(env_name, ', '.join(REGISTERED_ENVS)))
    return REGISTERED_ENVS[env_name](*args, **kwargs)


class EnvMeta(type):
    def __new__(meta, name, bases, class_dict):
        cls = super().__new__(meta, name, bases, class_dict)
        register_env(cls)
        return cls


class MujocoEnv(object, metaclass=EnvMeta):
    def __init__(self, display=True, control_freq=100, horizon=500, ignore_done=False, **kwargs):
        """
            Initialize a Mujoco Environment
            @display: If true, render the simulation state in a viewer instead of headless mode.
            @control_freq in Hz, how many control signals to receive in every second
            @ignore_done: if True, never terminate the env

            TODO(extension): What about control_freq = a + bN(0,1) to simulate imperfect timing
        """

        ### TODO: fix @_load_model if needed ###
        # self._load_model()
        # self.mjpy_model = self.model.get_model(mode='mujoco_py')
        # self.sim = MjSim(self.mjpy_model)
        # self.initialize_time(control_freq)
        # self.viewer = MujocoPyRenderer(self.sim)
        # self.sim_state_initial = self.sim.get_state()
        # self._get_reference()
        # self.done = False
        # self.t = 0
        self.display = display
        self.control_freq = control_freq
        self.horizon = horizon
        self.ignore_done = ignore_done
        self.viewer = None
        self._reset_internal()

        # for key in kwargs:
        #     print('Warning: Parameter {} not recognized'.format(key))


    def initialize_time(self, control_freq):
        """
            Initialize the time constants used for simulation
        """
        self.cur_time = 0
        self.model_timestep = self.sim.model.opt.timestep
        if self.model_timestep <= 0:
            raise XMLError('xml model defined non-positive time step')
        self.control_freq = control_freq
        if control_freq <= 0:
            raise SimulationError('control frequency {} is invalid'.format(control_freq))
        self.control_timestep = 1 / control_freq

    def _load_model(self):
        """Loads an xml model, puts it in self.model"""
        self.model = None

    def _get_reference(self):
        """Set up necessary reference for objects"""
        pass

    def reset(self):
        # if there is an active viewer window, destroy it
        self.close()
        self._reset_internal()
        return self._get_observation()

    def _reset_internal(self):
        # self.sim.set_state(self.sim_state_initial)
        self._load_model()
        self.mjpy_model = self.model.get_model(mode='mujoco_py')
        self.sim = MjSim(self.mjpy_model)
        self.initialize_time(self.control_freq)
        if self.display:
            self.viewer = MujocoPyRenderer(self.sim)
        self.sim_state_initial = self.sim.get_state()
        self._get_reference()
        self.cur_time = 0
        self.t = 0
        self.done = False

    def _get_observation(self):
        """
            Returns an OrderedDict containing observations [(name_string, np.array), ...]
        """
        return OrderedDict()

    def step(self, action):
        reward = 0
        info = None
        if not self.done:
            self.t += 1
            self._pre_action(action)
            end_time = self.cur_time + self.control_timestep
            while self.cur_time < end_time:
                self.sim.step()
                self.cur_time += self.model_timestep
            reward, done, info = self._post_action(action)
            return self._get_observation(), reward, done, info
        else:
            raise ValueError('executing action in terminated episode')

    def _pre_action(self, action):
        self.sim.data.ctrl[:] = action

    def _post_action(self, action):
        reward = self.reward(action)
        self.done = (self._check_terminated() or self.t >= self.horizon) and (not self.ignore_done)
        # TODO: how to manage info?
        return reward, self.done, {}

    def reward(self, action):
        return 0

    def render(self, camera_id=0):
        self.viewer.render(camera_id=camera_id)

    def observation_spec(self):
        return OrderedDict()

    def action_spec(self):
        raise NotImplementedError

    def reset_from_xml_string(self, xml_string):
        """
        Reloads the environment from an XML description of the environment.
        """

        # if there is an active viewer window, destroy it
        self.close()

        # load model from xml
        self.mjpy_model = load_model_from_xml(xml_string)

        self.sim = MjSim(self.mjpy_model)
        self.initialize_time(self.control_freq)
        if self.display:
            self.viewer = MujocoPyRenderer(self.sim)
        self.sim_state_initial = self.sim.get_state()
        self._get_reference()
        self.cur_time = 0
        self.t = 0
        self.done = False

    def _check_contact(self):
        """
        Returns True if gripper is in contact with an object.
        """
        return False

    def close(self):
        """
        Do any cleanup necessary here.
        """
        # if there is an active viewer window, destroy it
        if self.viewer is not None:
            self.viewer.close() # change this to viewer.finish()?
            self.viewer = None