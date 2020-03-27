
class Unit(object):

    # Abilities
    # main
    # secondary
    # react
    # support
    # move
    # For now, multi-hot skills,
    # multi-hot equipment
    def __init__(self, name, gender, brave, faith, zodiac, fft_class, abilities, equipment):
        self.name = name
        self.gender = gender
        self.brave = brave
        self.faith = faith
        self.zodiac = zodiac
        self.fft_class = fft_class
        self.abilities = abilities
        self.equipment = equipment

    def to_vec(self):
        pass

def unit_from_json(json):
    name = json["name"]
    gender = json["gender"]
    zodiac = json["zodiac"]
    brave = int(json["brave"])
    faith = int(json["faith"])
    fft_class = json["class"]["name"]
    abilities = []
    a = json["abilities"]
    for i in a["mainActive"]["learned"]:
        abilities.append(i["name"])
    for i in a["subActive"]["learned"]:
        abilities.append(i["name"])
    abilities.append(a["react"]["name"])
    abilities.append(a["support"]["name"])
    abilities.append(a["move"]["name"])
    equipment = []
    for i in json["equipment"]:
        equipment.append(i["name"])
    return Unit(name, gender, brave, faith, zodiac, fft_class, abilities, equipment)

# Team = [Unit]
# Match = (Team1, Team2, Map)
# Label - 0 or 1, Team1 or Team2

