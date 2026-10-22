# Review notes

Only the XPHB entries in `raw_data/spell/spells-xphb.json` were used. No 2014
restrictions or scaling were imported. All allegiance-neutral targeting is `any`;
an engine policy can prefer allies or enemies without changing legal targets.
Spatial restrictions are declarations for the engine heuristic, not simulated positions.

## Fire Bolt
- Creature **or object** is legal; separate `creature_or_object` union filter avoids requiring both types.
- Unworn/uncarried flammable-object ignition is unsupported; damage is retained.

## Eldritch Blast
- XPHB permits objects. Each beam has an independent attack and may repeat a target; upgrades add beams, not damage dice to one hit.

## Sacred Flame
- Ignores only Half and Three-Quarters Cover for its save; visibility is still required. No damage on success.

## Magic Missile
- Simultaneous darts, no attack/save; Shield suppresses all darts directed at a protected creature, including the triggering volley.
- Chose one shared `1d4 + 1` roll for the volley. The entry says simultaneous but does not explicitly settle shared versus independent rolls; this is a reviewable DM judgment. Dart counts and per-dart assignments remain separate.

## Guiding Bolt
- Advantage belongs to the next **attacker against the target**, not to the target. It is consumed even on a miss; damage does not consume it.
- Exact expiry is the end of the caster's next turn, overriding a literal fixed-length interpretation of the metadata's one round.

## Cure Wounds
- Uses `2d8 + spell_mod`, adding `2d8` per slot; XPHB has no undead/construct exclusion.

## Healing Word
- Uses `2d4 + spell_mod`, adding `2d4` per slot, and requires visibility; no undead/construct exclusion.

## Bless
- Up to three distinct creatures, not necessarily allies; each attack/save rolls a fresh d4. No ability-check benefit.
- Holy Symbol minimum value is 5 GP, unconsumed; source cost in copper was converted to GP.

## Shield
- +5 AC rechecks the triggering hit before hit effects. The reaction is not offered for an arbitrary attack that has not hit, except Magic Missile targeting.
- Ends at the start of the caster's next turn; the `shielded` marker is explicitly consumed as a damage guard by Magic Missile, not as generic damage immunity.

## Hex
- Any attack roll can trigger the extra damage. Chosen-ability disadvantage is for checks, never saving throws.
- Rebinding retains the ability and duration; a zero-HP drop is remembered even if the old target later heals. Transfer requires a later turn. Applied the original visible/in-range targeting restrictions to the new curse despite the transfer sentence not repeating them.
- Exact XPHB tiers are slot 2: 4 hours, slots 3–4: 8 hours, slots 5+: 24 hours. Concentration still applies.

## Hunter's Mark
- Force damage on **any** attack-roll hit, not merely weapon attacks. Unlike Hex, transfer can occur on the same turn if a bonus action is available.
- Finding the quarry with Wisdom (Perception/Survival) advantage is unsupported tracking. Slot 2 leaves duration unchanged; slots 3–4 give 8 hours, slots 5+ give 24 hours.

## Hold Person
- Humanoid and visibility restrictions remain on every upcast target. Each target's end-turn successful repeat save ends only its own participation.

## Scorching Ray
- Three independent attacks, with repeat targets allowed. Read unqualified “target” as permitting creatures or objects; text does not limit it to creatures.
- Each higher slot adds one ray, not extra dice per ray.

## Spiritual Weapon
- XPHB **requires concentration** and adds `1d8` for **every** slot above 2. One optional attack on creation and a bonus-action attack on later turns share one scalable block.
- Initial placement within 60 feet, 20-foot command movement, and 5-foot reach are recorded; exact placement/movement are unsupported. The force is not a creature with its own turn and is not tethered to the caster's original range.

## Fireball
- 20-foot-radius sphere with no allegiance exemption; the engine owns target counts. Successful saves halve damage.
- Unworn/uncarried flammable-object ignition is unsupported. No 2014 around-corners language was added.

## Spirit Guardians
- Uses the three XPHB triggers: aura enters a creature's space, creature enters aura, or creature ends its turn there. Save limit is once per creature per **any** turn across all three triggers, not once per round. No start-turn damage.
- Chose not to count initial aura creation itself as entry; this geometric ambiguity needs DM review. Movement triggers are declarative only until the engine supplies abstract entry events; speed halving remains a recorded no-op. Exemptions are fixed at casting, without an invented visibility requirement.
- Damage type is constrained by alignment (good/neutral radiant, evil necrotic), not freely chosen. Spectral appearance is unsupported cosmetic detail.

## Haste
- Granted action is once per recipient turn with exactly the listed options; Attack permits one attack only. It is not an unrestricted action-count increase.
- On any ending, remove buffs and apply **Incapacitated** plus speed 0 through the end of the target's next turn. These end effects survive spell cleanup; both speed changes are recorded no-ops in this simulator.

## Counterspell
- Constitution save by the interrupted caster, not a spellcasting check or spell-level contest. Requires a visible caster within 60 feet and at least one V/S/M component.
- Failure wastes the casting action/bonus action/reaction but does not expend the interrupted spell's slot. No refund is promised for other resources; the reacting caster's own Counterspell slot is still spent normally.

## Banishment
- Incapacitated and removed from combat on failed Charisma save, with no repeated save. At a full minute the five listed creature types do not return, regardless of native plane; other types return normally.
- Return predicate runs before cleanup. Early concentration loss returns all affected types; conditions end even for a nonreturning creature. Upcast targets each save separately.
- Demiplane details, destination plane/location selection, and original/nearest-unoccupied return positioning are unsupported; permanent combat removal is still modeled.

## Shield of Faith
- +2 AC for up to 10 minutes with concentration. XPHB requires neither visibility nor willingness; no such filters were added.
