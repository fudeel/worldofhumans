# game/main.py
"""
Terminal entry point for character creation.

Walks the player through race and class selection with full
validation, then displays the created character's summary.
"""

from game.characters.character import Character
from game.definitions import CLASS_REGISTRY, get_class_definition
from game.enums.character_class_type import CharacterClassType
from game.enums.race import Race
from game.enums.resource_type import ResourceType


def _prompt_choice(label: str, options: list) -> object:
    """
    Present a numbered list and return the chosen item.

    Re-prompts until a valid number is entered.
    """
    print(f"\n=== {label} ===")
    for idx, option in enumerate(options, start=1):
        print(f"  {idx}. {option.value}")
    while True:
        raw = input("Pick a number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        print("  Invalid choice, try again.")


def _prompt_name() -> str:
    """Ask the player to enter a character name."""
    while True:
        name = input("\nEnter character name: ").strip()
        if name:
            return name
        print("  Name cannot be empty.")


def _display_character(char: Character) -> None:
    """Print a formatted summary of the newly created character."""
    cdef = char.class_definition
    print("\n" + "=" * 50)
    print(f"  {char.name}")
    print(f"  Level {char.level} {char.race.value} {char.class_name}")
    print(f"  Faction: {char.faction.value}")
    print(f"  Health:  {char.health.current}/{char.health.maximum}")
    for rtype, pool in char.resources.items():
        print(f"  {rtype.value}:  {pool.current}/{pool.maximum}")
    print(f"  Roles:   {', '.join(r.value for r in sorted(cdef.roles, key=lambda r: r.value))}")
    print(f"  Talents: {' / '.join(cdef.talent_trees)}")
    print("=" * 50)


def _filter_classes_for_race(race: Race) -> list[CharacterClassType]:
    """Return class types available to *race*."""
    return [
        ct for ct, cdef in CLASS_REGISTRY.items()
        if cdef.supports_race(race)
    ]


def run() -> None:
    """Execute the character creation flow in the terminal."""
    print("=" * 50)
    print("       CLASSIC WoW — CHARACTER CREATION")
    print("=" * 50)

    # Step 1: Pick a race
    races = sorted(Race, key=lambda r: r.value)
    race = _prompt_choice("Choose your Race", races)

    # Step 2: Pick a class (filtered by race)
    available = _filter_classes_for_race(race)
    if not available:
        print(f"\nNo classes available for {race.value}.")
        return
    class_type = _prompt_choice("Choose your Class", available)
    class_def = get_class_definition(class_type)

    # Step 3: Name
    name = _prompt_name()

    # Step 4: Create and display
    character = Character(
        name=name,
        race=race,
        class_def=class_def,
        level=1,
        base_health=100,
    )
    _display_character(character)


if __name__ == "__main__":
    run()