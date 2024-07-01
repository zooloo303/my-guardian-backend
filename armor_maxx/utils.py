SUBCLASS_TO_ELEMENT_MAP = {
    # Titan Subclasses
    "1616346845": "Prismatic",
    "2932390016": "Arc",    # Striker
    "2842471112": "Void",   # Sentinel
    "2550323932": "Solar",  # Sunbreaker
    "613647804": "Stasis", # Behemoth
    "242419885": "Strand", # Berserker

    # Hunter Subclasses
    "4282591831": "Prismatic",
    "2328211300": "Arc",    # Arcstrider
    "2453351420": "Void",   # Nightstalker
    "2240888816": "Solar",  # Gunslinger
    "873720784": "Stasis",  # Revenant
    "3785442599": "Strand", # Threadrunner

    # Warlock Subclasses
    "3893112950": "Prismatic",
    "3168997075": "Arc",    # Stormcaller
    "2849050827": "Void",   # Voidwalker 
    "3941205951": "Solar",  # Dawnblade
    "3291545503": "Stasis", # Shadebinder
    "4204413574": "Strand", # Broodweaver
}

def get_element_from_subclass(subclass_id):
    return SUBCLASS_TO_ELEMENT_MAP.get(subclass_id, "Unknown")

# destinyEnums
ARMOR_CATEGORY_HASHES = {
    'HELMET': 45,
    'GAUNTLETS': 46,
    'CHEST_ARMOR': 47,
    'LEG_ARMOR': 48,
    'CLASS_ARMOR': 49,
}

CLASS_CATEGORY_HASHES = {
    'WARLOCK': 21,
    'TITAN': 22,
    'HUNTER': 23, 
}

def get_armor_type(item_category_hashes):
    if not item_category_hashes:
        return None

    for armor_type, hash_value in ARMOR_CATEGORY_HASHES.items():
        if hash_value in item_category_hashes:
            return armor_type

    # If we reach here, no matching armor type was found
    return None

def get_item_class(item_category_hashes):
    for class_name, hash_value in CLASS_CATEGORY_HASHES.items():
        if hash_value in item_category_hashes:
            return class_name
    return 'ALL'  # If no class-specific hash is found, assume it's for all classes