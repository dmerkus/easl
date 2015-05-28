
"""
Containing the experiment based on the mobile experiment.
"""
import functools

from easl import *
from easl.controller import *
from easl.visualize import *


#
# Infant functions
#

def calc_direction(a, b):
    """
    Calculates which direction b is from a.
    """
    d = {"down": -1, "middle": 0, "up": 1}

    if d[a] == d[b]:
        return "still"
    if d[a] < d[b]:
        return "up"
    if d[a] > d[b]:
        return "down"


def new_position(position, direction):
    if direction == "still" or direction == "up" and position == "up" or direction == "down" and position == "down":
        # Already at maximum, so nothing changes
        return position
    elif direction == "up":
        if position == "down":
            return "middle"
        if position == "middle":
            return "up"
    elif direction == "down":
        if position == "up":
            return "middle"
        if position == "middle":
            return "down"

    raise RuntimeError("Unhandled movement {1} from {0}.".format(position, direction))


def relative_direction(self, value, attribute):
    """
    Callback function for the infant's limbs.
    """
    self.try_change(attribute, new_position(self.a[attribute], value))


def move(old, new):
    return "movement", {"direction": calc_direction(old, new)}


#
# Mobile functions
#

def swing(self):
    speed = self.a["velocity"]

    self.try_change("velocity", max(0, min(speed - 1, 10)))


def swing_direction(self):
    v = self.a["velocity"]
    p = self.a["position"]
    d = self.a["direction"]

    if d == "+":
        p_new = p + v
        if p_new <= 10:
            self.try_change("position", p_new)
        else:
            self.try_change("position", 10 - (p_new - 10))
            self.try_change("direction", "-")
    elif d == "-":
        p_new = p - v
        if p_new >= 0:
            self.try_change("position", p_new)
        else:
            self.try_change("position", abs(p_new))
            self.try_change("direction", "+")
    else:
        raise RuntimeError("HUH?")

    # Decay
    self.try_change("velocity", max(0, min(v - 1, 10)))


def moved(self, direction):
    self.a["previous"] = self.a["velocity"]
    self.a["velocity"] += 4


def moved_direction(self, direction):
    self.a["previous"] = self.a["velocity"]
    if self.a["direction"] == "+":
        self.a["velocity"] = abs(self.a["velocity"] - 3)
    elif self.a["direction"] == "-":
        self.a["velocity"] = min(self.a["velocity"] + 3, 10)
    self.a["direction"] = "-"


def movement_emission_boolean(self):
    s = []
    if self.a["velocity"] > 0:
        s.append(Signal("sight", "movement", True, [True, False]))

    return s


def movement_emission_change(self):
    s = []

    if self.a["velocity"] == 0:
        s.append(Signal("sight", "movement", "idle", ["idle", "faster", "slower", "same"]))
    elif self.a["velocity"] > self.a["previous"]:
        s.append(Signal("sight", "movement", "faster", ["idle", "faster", "slower", "same"]))
    elif self.a["velocity"] < self.a["previous"]:
        s.append(Signal("sight", "movement", "slower", ["idle", "faster", "slower", "same"]))
    else:
        s.append(Signal("sight", "movement", "same", ["idle", "faster", "slower", "same"]))

    return s


class SightSensorBoolean(Sensor):
    def init(self):
        self.signals.update({"movement": [True, False]})
        self.default_signals.update({"movement": False})

    def detects_modality(self, modality):
        return modality == "sight"


class SightSensorChange(Sensor):
    def init(self):
        self.signals.update({"movement": ["idle", "faster", "slower", "same"]})
        self.default_signals.update({"movement": "idle"})

    def detects_modality(self, modality):
        return modality == "sight"


class InfantVisual(Visual):
    @staticmethod
    def visualize(self):
        p = {"up": 0, "middle": 1, "down": 2}

        grid = Grid("infant", 2, 2)

        grid.add_element(Slider("left-hand-position", 3, p[self.a["left-hand-position"]]), 0, 0)
        grid.add_element(Slider("right-hand-position", 3, p[self.a["right-hand-position"]]), 0, 1)
        grid.add_element(Slider("left-foot-position", 3, p[self.a["left-foot-position"]]), 1, 0)
        grid.add_element(Slider("right-foot-position", 3, p[self.a["right-foot-position"]]), 1, 1)

        return grid


def create_infant(agent):
    """
    Parameters
    ----------
    controller : string
        Name of the type of controller to use.
    """
    infant = Entity("infant", visual=InfantVisual())

    if agent == "random":
        infant.set_agent(RandomController())
    elif agent == "operant":
        infant.set_agent(OperantConditioningController())
        infant.agent.set_primary_reinforcer("movement", "faster")
    elif agent == "causal":
        cla = CausalLearningController()
        cla.set_values({"movement": "faster"})
        infant.set_agent(cla)
    elif agent == "simple":
        infant.set_agent(SimpleController([("movement", "faster")]))
    else:
        raise RuntimeError("Undefined controller type.")

    infant.add_attribute("left-hand-position", "down", ["down", "middle", "up"], move)
    infant.add_attribute("right-hand-position", "down", ["down", "middle", "up"], move)
    infant.add_attribute("left-foot-position", "down", ["down", "middle", "up"], move)
    infant.add_attribute("right-foot-position", "down", ["down", "middle", "up"], move)

    infant.add_action("left-hand",
                      ["up", "still", "down"],
                      "still",
                      functools.partial(relative_direction, attribute="left-hand-position"))

    infant.add_action("right-hand",
                      ["up", "still", "down"],
                      "still",
                      functools.partial(relative_direction, attribute="right-hand-position"))

    infant.add_action("left-foot",
                      ["up", "still", "down"],
                      "still",
                      functools.partial(relative_direction, attribute="left-foot-position"))

    infant.add_action("right-foot",
                      ["up", "still", "down"],
                      "still",
                      functools.partial(relative_direction, attribute="right-foot-position"))

    infant.add_sensor(SightSensorChange())

    return infant


def create_mobile_boolean():
    mobile = Entity("mobile")

    mobile.add_attribute("velocity", 0, range(0, 10), lambda old, new: None)
    mobile.set_physics(swing)

    mobile.add_trigger("movement", moved)
    mobile.set_emission(movement_emission_boolean)

    return mobile


class MobileVisual(Visual):
    @staticmethod
    def visualize(self):
        group = Group("mobile")
        group.add_element(Number("velocity", self.a["velocity"]))
        group.add_element(Circle("velocity", 0, 10, self.a["velocity"]))

        return group


class MobileDirectionVisual(Visual):
    @staticmethod
    def visualize(self):
        group = Group("mobile")
        group.add_element(Number("velocity", self.a["velocity"]))
        # Invert the slider (direction down is up)
        group.add_element(Slider("position", 11, 10 - self.a["position"]))
        group.add_element(Circle("velocity", 0, 10, self.a["velocity"]))

        return group

def create_mobile_change():
    mobile = Entity("mobile", visual=MobileVisual())

    mobile.add_attribute("velocity", 0, range(0, 10), lambda old, new: None)
    mobile.add_attribute("previous", 0, range(0, 10), lambda old, new: None)

    mobile.set_physics(swing)

    mobile.add_trigger("movement", moved)
    mobile.set_emission(movement_emission_change)

    return mobile


def create_mobile_direction():
    mobile = Entity("mobile", visual=MobileDirectionVisual())

    mobile.add_attribute("position", 5, range(0, 10), lambda old, new: None)
    mobile.add_attribute("velocity", 0, range(0, 10), lambda old, new: None)
    mobile.add_attribute("previous", 0, range(0, 10), lambda old, new: None)
    mobile.add_attribute("direction", "+", ["+", "-"], lambda old, new: None)

    mobile.set_physics(swing_direction)

    mobile.add_trigger("movement", moved_direction)
    mobile.set_emission(movement_emission_change)

    return mobile


def create_experimenter(experiment_log):
    """
    Parameters
    ----------
    log : Log
        Log to play back kicking behavior from.
    """
    experimenter = Entity("experimenter")
    # second argument is dictionary of which actions of the original log match which actions.
    agent = LogController("infant", experiment_log)
    agent.set_watched("right-foot-position", "mechanical-hand", calc_direction)
    experimenter.set_agent(agent)

    experimenter.add_attribute("mechanical-hand-position", "down", ["down", "middle", "up"], move)

    experimenter.add_action("mechanical-hand",
                            ["up", "still", "down"],
                            "still",
                            functools.partial(relative_direction, attribute="mechanical-hand-position"))

    return experimenter


def experimental_condition(n, agent, v=None, remove={}, add={}):
    infant = create_infant(agent)
    mobile = create_mobile_change()

    world = World(v)
    world.add_entity(infant)
    world.add_entity(mobile)
    world.add_trigger("infant", "right-foot-position", "movement", "mobile")

    world.run(n, add_triggers=add, remove_triggers=remove)

    return world.log


def control_condition(n, experiment_log, agent, v=None):
    infant = create_infant(agent)
    mobile = create_mobile_change()
    experimenter = create_experimenter(experiment_log)

    world = World(v)
    world.add_entity(infant)
    world.add_entity(mobile)
    world.add_entity(experimenter)
    world.add_trigger("experimenter", "mechanical-hand-position", "movement", "mobile")

    world.run(n)

    return world.log


if __name__ == '__main__':
    v = PyGameVisualizer()

    remove_triggers = {40: [("infant", "right-foot-position", "movement", "mobile")]}
    add_triggers = {40: [("infant", "left-hand-position", "movement", "mobile")]}

    log = experimental_condition(120, "causal", v, add=add_triggers, remove=remove_triggers)
    log.make_kicking_data("data.csv")
    Log.make_bins("data", 6, ["lh", "rh", "lf", "rf"])

    #log = control_condition(100, log, "simple", v)

    #v.visualize_log(log)

    # log2 = control_condition(n, log)

    # v.visualize(log2)
