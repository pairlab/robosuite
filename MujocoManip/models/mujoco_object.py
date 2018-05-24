import copy
import time
import numpy as np
import xml.etree.ElementTree as ET
from MujocoManip.models.base import MujocoXML
from MujocoManip.miscellaneous import XMLError
from MujocoManip.models.model_util import *


class MujocoObject():
    """
        Base class for all objects
        We use Mujoco Objects to implement all objects that 
        1) may appear for multiple times in a task
        2) can be swapped between different tasks
        Typical methods return copy so the caller can all joints/attributes as wanted
    """
    def __init__(self):
        self.asset = ET.Element('asset')

    def get_bottom_offset(self):
        """
            Returns vector from object center to object bottom
            Helps us put objects on a surface
            returns numpy array
            e.g. return np.array([0, 0, -2])
        """
        raise NotImplementedError
        

    def get_top_offset(self):
        """
            Returns vector from object center to object top
            Helps us put other objects on this object
            returns numpy array
            e.g. return np.array([0, 0, 2])
        """
        raise NotImplementedError

    def get_horizontal_radius(self):
        """
            Returns scalar 
            If object a,b has horizontal distance d
                a.get_horizontal_radius() + b.get_horizontal_radius() < d 
                should mean that a, b has no contact 
            Helps us put objects programmatically without them flying away due to 
            a huge initial contact force
        """
        raise NotImplementedError
        # return 2

    def get_collision(self):
        """
            Returns a ET.Element
            It is a <body/> subtree that defines all collision related stuff of this object
            Return is a copy
        """
        raise NotImplementedError
        
    def get_visual(self, name=None):
        """
            Returns a ET.Element
            It is a <body/> subtree that defines all visual related stuff of this object
            Return is a copy
        """
        raise NotImplementedError

    def get_full(self, name=None, site=False):
        """
            Returns a ET.Element
            It is a <body/> subtree that defines all collision and visual related stuff of this object
            Return is a copy
        """
        print('[Warning] Get full is deprecated')
        collision = self.get_collision(name=name, site=site)
        visual = self.get_visual()
        collision.append(visual)

        return collision

    def get_site_attrib_template(self):
        return {
                'pos': '0 0 0',
                'size': '0.002 0.002 0.002',
                'rgba': '1 0 0 1',
                'type': 'sphere',
                }

class MujocoXMLObject(MujocoXML, MujocoObject):
    """
        MujocoObjects that are loaded from xml files
    """
    def __init__(self, fname):
        MujocoXML.__init__(self, fname)

    def get_bottom_offset(self):
        bottom_site = self.worldbody.find("./site[@name='bottom_site']")
        return string_to_array(bottom_site.get('pos'))

    def get_top_offset(self):
        top_site = self.worldbody.find("./site[@name='top_site']")
        return string_to_array(top_site.get('pos'))

    def get_horizontal_radius(self):
        horizontal_radius_site = self.worldbody.find("./site[@name='horizontal_radius_site']")
        return string_to_array(horizontal_radius_site.get('pos'))[0]

    def get_collision(self, name=None, site=False):
        collision = copy.deepcopy(self.worldbody.find("./body[@name='collision']"))
        collision.attrib.pop('name')
        if name is not None:
            collision.attrib['name'] = name #.set('name', name)
        if site:
            # add a site as well
            template = self.get_site_attrib_template()
            if name is not None:
                template['name'] = name
            collision.append(ET.Element('site', attrib=template))
        return collision

    def get_visual(self, name=None, site=False):
        visual = copy.deepcopy(self.worldbody.find("./body[@name='visual']"))
        visual.attrib.pop('name')
        if name is not None:
            visual.attrib.set('name', name)
        if site:
            # add a site as well
            template = self.get_site_attrib_template()
            if name is not None:
                template['name'] = name
            visual.append(ET.Element('site', attrib=template))
        return visual

class DefaultStockPotObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/object_pot.xml'))

class DefaultHoleObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/object_hole.xml'))

class DefaultBoxObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/object_box.xml'))

class DefaultBallObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/object_ball.xml'))

class DefaultCylinderObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/object_cylinder.xml'))

class DefaultCapsuleObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/object_capsule.xml'))

class DefaultBottleObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/bottle.xml'))

class DefaultMugObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/mug.xml'))

class DefaultPotObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/pot.xml'))
        
class DefaultBowlObject(MujocoXMLObject):
    def __init__(self):
        super().__init__(xml_path_completion('object/bowl.xml'))

class MujocoGeneratedObject(MujocoObject):
    """
        Base class for all programmatically generated mujoco object
        i.e., every MujocoObject that does not have an corresponding xml file 
    """
    def __init__(self, size=None, rgba=None, density=None, friction=None,
                density_range=None, friction_range=None):
        """
            Provides default initialization of physical attributes:
            - size([float] of size 1 - 3)
            - rgba([float, float, float, float])
            - density(float)
            - friction(float) for tangential friction
            see http://www.mujoco.org/book/modeling.html#geom for details
            also supports randomization of (rgba, density, friction). 
            - rgb is randomly generated if rgba='random' (alpha will be 1 in this case)
            - If density is None and density_range is not:
              Density is chosen uniformly at random specified from density range, 
              i.e. density_range = [50, 100, 1000]
            - If friction is None and friction_range is not:
              Tangential Friction is chosen uniformly at random from friction_range
            TODO: do we want rotational friction?
        """
        super().__init__()
        if size is None:
            self.size = [0.05, 0.05, 0.05]
        else:
            self.size = size

        if rgba is None:
            self.rgba = [1, 0, 0, 1]
        elif rgba == 'random':
            self.rgba = np.array([np.random.uniform(0, 1) for i in range(3)] + [1])
        else:
            assert len(rgba) == 4, 'rgba must be a length 4 array'
            self.rgba = rgba

        if density is None:
            if density_range is not None:
                self.density = np.random.choice(density_range)
            else:
                self.density = 1000 # water
        else:
            self.density = density

        if friction is None:
            if friction_range is not None:
                self.friction = [np.random.choice(friction_range), 0.005, 0.0001]
            else:
                self.friction = [1, 0.005, 0.0001] # Mujoco default
        elif hasattr(type(friction), '__len__'):
            assert len(friction) == 3, 'friction must be a length 3 array or a float'
            self.friction = friction
        else:
            self.friction = [friction, 0.005, 0.0001]
        self.sanity_check()

    def sanity_check(self):
        """
            Checks if data provided makes sense.
            Called in __init__()
            For subclasses to inherit from
        """
        pass

    # Here we are setting group = 1 as this is the only geom group that mujoco
    # displays by default
    def get_collision_attrib_template(self):
        return {'pos': '0 0 0', 'group': '1'}

    def get_visual_attrib_template(self):
        return {'conaffinity': "0", 'contype': "0", 'group': '1'}

    # returns a copy, Returns xml body node
    def _get_collision(self, name=None, site=False, ob_type='box'):
        body = ET.Element('body')
        if name is not None:
            body.set('name', name)
        template = self.get_collision_attrib_template()
        if name is not None:
            template['name'] = name
        template['type'] = ob_type
        template['rgba'] = array_to_string(self.rgba)
        template['size'] = array_to_string(self.size)
        template['density'] = str(self.density)
        template['friction'] = array_to_string(self.friction)
        body.append(ET.Element('geom', attrib=template))
        if site:
            # add a site as well
            template = self.get_site_attrib_template()
            if name is not None:
                template['name'] = name
            body.append(ET.Element('site', attrib=template))
        return body

    # returns a copy, Returns xml body node
    def _get_visual(self, name=None, site=False, ob_type='box'):
        body = ET.Element('body')
        if name is not None:
            body.set('name', name)
        template = self.get_visual_attrib_template()
        template['type'] = ob_type
        template['rgba'] = array_to_string(self.rgba)
        template['size'] = array_to_string(self.size) 
        body.append(ET.Element('geom', attrib=template))
        if site:
            # add a site as well
            template = self.get_site_attrib_template()
            if name is not None:
                template['name'] = name
            body.append(ET.Element('site', attrib=template))
        return body

class BoxObject(MujocoGeneratedObject):
    """
        An object that is a box
    """
    def sanity_check(self):
        assert len(self.size) == 3, 'box size should have length 3'

    def get_bottom_offset(self):
        return np.array([0, 0, -1 * self.size[2]])

    def get_top_offset(self):
        return np.array([0, 0, self.size[2]])

    def get_horizontal_radius(self):
        return np.linalg.norm(self.size[0:2], 2)

    # returns a copy, Returns xml body node
    def get_collision(self, name=None, site=False):
        return self._get_collision(name=name, site=site, ob_type='box')
    
    # returns a copy, Returns xml body node
    def get_visual(self, name=None, site=False):
        return self._get_visual(name=name, site=site, ob_type='box')

class CylinderObject(MujocoGeneratedObject):
    """
        An object that is a cylinder
    """
    def sanity_check(self):
        assert len(self.size) == 2, 'cylinder size should have length 2'

    def get_bottom_offset(self):
        return np.array([0, 0, -1 * self.size[1]])

    def get_top_offset(self):
        return np.array([0, 0, self.size[1]])

    def get_horizontal_radius(self):
        return self.size[0]

    # returns a copy, Returns xml body node
    def get_collision(self, name=None, site=False):
        return self._get_collision(name=name, site=site, ob_type='cylinder')
    
    # returns a copy, Returns xml body node
    def get_visual(self, name=None, site=False):
        return self._get_visual(name=name, site=site, ob_type='cylinder')

class BallObject(MujocoGeneratedObject):
    """
        An object that is a ball (sphere)
    """
    def sanity_check(self):
        assert len(self.size) == 1, 'ball size should have length 1'

    def get_bottom_offset(self):
        return np.array([0, 0, -1 * self.size[0]])

    def get_top_offset(self):
        return np.array([0, 0, self.size[0]])

    def get_horizontal_radius(self):
        return self.size[0]

    # returns a copy, Returns xml body node
    def get_collision(self, name=None, site=False):
        return self._get_collision(name=name, site=site, ob_type='sphere')
    
    # returns a copy, Returns xml body node
    def get_visual(self, name=None, site=False):
        return self._get_visual(name=name, site=site, ob_type='sphere')

class CapsuleObject(MujocoGeneratedObject):
    """
        An object that is a capsule 
    """
    # TODO: friction, etc
    def sanity_check(self):
        assert len(self.size) == 2, 'capsule size should have length 2'

    def get_bottom_offset(self):
        return np.array([0, 0, -1 * (self.size[0] + self.size[1])])

    def get_top_offset(self):
        return np.array([0, 0, (self.size[0] + self.size[1])])

    def get_horizontal_radius(self):
        return self.size[0]

    # returns a copy, Returns xml body node
    def get_collision(self, name=None, site=False):
        return self._get_collision(name=name, site=site, ob_type='capsule')
    
    # returns a copy, Returns xml body node
    def get_visual(self, name=None, site=False):
        return self._get_visual(name=name, site=site, ob_type='capsule')


DEFAULT_DENSITY_RANGE = [200, 500, 1000, 3000, 5000]
DEFAULT_FRICTION_RANGE = [0.25, 0.5, 1, 1.5, 2]

class RandomBoxObject(BoxObject):
    """
        A random box
    """
    def __init__(self, size_max=None, size_min=None,
                density_range=None, 
                friction_range=None,
                rgba='random'):
        if size_max is None:
            size_max = [0.07, 0.07, 0.07]
        if size_min is None:
            size_min = [0.03, 0.03, 0.03]
        size = np.array([np.random.uniform(size_min[i], size_max[i]) for i in range(3)])
        if density_range is None:
            density_range = DEFAULT_DENSITY_RANGE
        if friction_range is None:
            friction_range = DEFAULT_FRICTION_RANGE
        super().__init__(size=size, rgba=rgba, 
                        density_range=density_range, 
                        friction_range=friction_range)


class RandomCylinderObject(CylinderObject):
    """
        A random cylinder
    """
    def __init__(self, size_max=None, size_min=None,
                density_range=None, 
                friction_range=None,
                rgba='random'):
        if size_max is None:
            size_max = [0.07, 0.07]
        if size_min is None:
            size_min = [0.03, 0.03]
        size = np.array([np.random.uniform(size_min[i], size_max[i]) for i in range(2)])
        if density_range is None:
            density_range = DEFAULT_DENSITY_RANGE
        if friction_range is None:
            friction_range = DEFAULT_FRICTION_RANGE
        super().__init__(size=size, rgba=rgba, 
                        density_range=density_range, 
                        friction_range=friction_range)


class RandomBallObject(BallObject):
    """
        A random ball (sphere)
    """
    def __init__(self, size_max=None, size_min=None, 
                density_range=None, 
                friction_range=None,
                rgba='random'):
        if size_max is None:
            size_max = [0.07]
        if size_min is None:
            size_min = [0.03]
        size = np.array([np.random.uniform(size_min[i], size_max[i]) for i in range(1)])
        if density_range is None:
            density_range = DEFAULT_DENSITY_RANGE
        if friction_range is None:
            friction_range = DEFAULT_FRICTION_RANGE
        super().__init__(size=size, rgba=rgba, 
                        density_range=density_range, 
                        friction_range=friction_range)


class RandomCapsuleObject(CapsuleObject):
    """
        A random ball (sphere)
    """
    def __init__(self, size_max=None, size_min=None, rgba='random'):
        if size_max is None:
            size_max = [0.07, 0.07]
        if size_min is None:
            size_min = [0.03, 0.03]
        size = np.array([np.random.uniform(size_min[i], size_max[i]) for i in range(2)])
        if density_range is None:
            density_range = DEFAULT_DENSITY_RANGE
        if friction_range is None:
            friction_range = DEFAULT_FRICTION_RANGE
        super().__init__(size=size, rgba=rgba, 
                        density_range=density_range, 
                        friction_range=friction_range)
