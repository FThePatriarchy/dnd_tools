"""Second review: exact oracles and disk-free regression mutations for A-F."""
from copy import deepcopy

from engine import Combat, Combatant
from engine.spell_mechanics import SpellMechanics
from engine.state import Effect
from test_engine_step3 import arena, spell_specs
from test_engine_step3_fixes import mutation_fails


def test_step3_fix2_A_transform_stack_and_depletion(monkeypatch):
    def oracle():
        for order in ['suppressed_first', 'effective_first', 'deplete']:
            b, c, (d, other) = arena('Polymorph', enemies=2)
            d.extra_attack = 3
            d.features = {'original': True}
            other.spells = ['Polymorph']; other.spell_slots = {4: 2}; other.spell_dc = 100
            original = deepcopy({k: getattr(d, k) for k in ['speed', 'extra_attack', 'attacks', 'features', 'abilities', 'level', 'cr']})
            first = b.cast(c, 'Polymorph', [d], choices={'form': 'wolf'})
            assert (d.speed, d.extra_attack, d.temp_hp, d.features) == (40, 1, 11, {'pack_tactics': True})
            b.damage(d, 3, 'force')
            assert d.temp_hp == 8
            b.begin_turn(other)
            second = b.cast(other, 'Polymorph', [d], choices={'form': 'riding horse'})
            assert second is not None  # CR is checked against the original, not Wolf CR.
            assert (d.speed, d.extra_attack, d.temp_hp, d.features) == (60, 1, 13, {})
            assert [e.suppressed for e in d.effects if e.kind == 'transform'] == [True, False]
            if order == 'suppressed_first':
                b.end_spell(first.id)
                assert second.active and other.concentration == second.id
                assert (d.speed, d.extra_attack, d.temp_hp, d.features) == (60, 1, 13, {})
                b.end_spell(second.id)
            else:
                if order == 'deplete':
                    hp = d.hp
                    b.damage(d, 15, 'force')
                    assert d.hp == hp - 2
                    assert not second.active and other.concentration is None
                else:
                    b.end_spell(second.id)
                assert first.active and c.concentration == first.id
                assert (d.speed, d.extra_attack, d.temp_hp, d.features) == (40, 1, 8, {'pack_tactics': True})
                if order == 'deplete':
                    b.damage(d, 8, 'force')
                    assert not first.active and c.concentration is None
                else:
                    b.end_spell(first.id)
            assert {k: getattr(d, k) for k in original} == original
            assert d.temp_hp == 0 and d.transform_snapshot is None and d.effective_transform is None
            assert not b.turn_rules(d).get('no_spells')
    oracle()
    mutation_fails(monkeypatch, SpellMechanics, 'spell_primitive',
                   'if target.transform_snapshot is None:', 'if True:', oracle)
    mutation_fails(monkeypatch, SpellMechanics, 'reconcile_transform',
                   'target.effective_transform.data["temp_hp"] = target.temp_hp', 'pass', oracle)
    mutation_fails(monkeypatch, SpellMechanics, 'deplete_transform',
                   'self.end_spell(instance.id)', 'pass', oracle)


def test_step3_fix2_B_allegiance_tracks_effective_charm(monkeypatch):
    def oracle():
        for name in ['Dominate Person', 'Dominate Beast']:
            b, c, (d, other) = arena(name, enemies=2)
            d.attacks = [{'name': 'Probe', 'kind': 'melee', 'to_hit': 100, 'effects': []}]
            inst = b.cast(c, name, [d])
            assert d.has_condition('charmed') and d.team == 'party'
            assert d.__dict__['team'] == 'enemy'
            assert b.enemies(d) == [other]
            b.begin_turn(d); b.log.clear(); b.weapon_action(d)
            assert [e['defender'] for e in b.log if e['event'] == 'attack'] == [other.id]
            if name == 'Dominate Person':
                other.spells = ['Calm Emotions']; other.spell_slots = {2: 1}
                b.area = lambda *_: [1]
                b.begin_turn(other)
                calm = b.cast(other, 'Calm Emotions', choices={'mode': 'immune'})
                assert calm is not None
            else:
                defense = Effect('defense', {'condition_immunity': ['charmed']}, 999, 'probe')
                d.effects.append(defense)
            assert not d.has_condition('charmed') and d.team == 'enemy'
            assert b.enemies(d) == [c]
            b.begin_turn(d); b.log.clear(); b.weapon_action(d)
            assert [e['defender'] for e in b.log if e['event'] == 'attack'] == [c.id]
            if name == 'Dominate Person': b.end_spell(calm.id)
            else: d.effects.remove(defense)
            assert inst.active and c.concentration == inst.id
            assert d.has_condition('charmed') and d.team == 'party'
            assert b.enemies(d) == [other]
            b.restore(d, 'charmed')
            assert not d.has_condition('charmed') and d.team == 'enemy'
            d.effects.append(Effect('apply_condition', {'condition': 'charmed', 'caster_id': c.id}, 999, 'unrelated'))
            assert d.has_condition('charmed') and d.team == 'enemy'
            b.end_spell(inst.id)
            assert d.team == 'enemy' and c.concentration is None
    oracle()
    # The public descriptor calls this getter dynamically through its fget.
    import pytest
    team = Combatant.team
    with monkeypatch.context() as patch:
        patch.setattr(Combatant, 'team', property(lambda actor: next(
            (e.data['control_team'] for e in reversed(actor.effects) if 'control_team' in e.data), actor.__dict__['team']), team.fset))
        with pytest.raises(AssertionError): oracle()


def test_step3_fix2_C_base_max_hp_and_active_bonuses(monkeypatch):
    def oracle():
        for restore_before_end in [True, False]:
            b, c, (d, drain) = arena('Aid', enemies=2)
            d.max_hp = d.hp = d.original_max_hp = 100
            aid = b.cast(c, 'Aid', [d], slot=2)
            assert (d.base_max_hp, d.spell_hp_bonus, d.max_hp, d.hp) == (100, 5, 105, 105)
            drain.features['life_drain'] = {'attacks': ['Drain'], 'type': 'all', 'heal': False}
            b._monster_attack = (drain, 'Drain')
            b.damage(d, 10, 'necrotic', drain)
            b._monster_attack = None
            assert (d.base_max_hp, d.spell_hp_bonus, d.max_hp, d.hp) == (90, 5, 95, 95)
            c.spells.append('Greater Restoration')
            if not restore_before_end:
                b.end_spell(aid.id)
                assert (d.base_max_hp, d.max_hp, d.hp) == (90, 90, 90)
            b.begin_turn(c)
            restoration = b.cast(c, 'Greater Restoration', [d], choices={'kind': 'max_hp'})
            assert restoration is not None
            assert (d.base_max_hp, d.max_hp, d.hp) == ((100, 105, 95) if restore_before_end else (100, 100, 90))
            b.refresh_spell_effects(); b.refresh_spell_effects()
            assert d.max_hp == (105 if restore_before_end else 100)
            b.end_spell(aid.id)
            assert (d.base_max_hp, d.spell_hp_bonus, d.max_hp, d.hp) == (100, 0, 100, 90)
        # Stronger-bonus suppression/resumption must not change the base either.
        b, c, (d,) = arena('Aid', enemies=1)
        d.max_hp = d.hp = d.original_max_hp = 100
        first = b.cast(c, 'Aid', [d], slot=2)
        b.begin_turn(c); second = b.cast(c, 'Aid', [d], slot=3)
        d.max_hp -= 10; d.hp = min(d.hp, d.max_hp)
        b.restore(d, 'max_hp')
        assert (d.base_max_hp, d.spell_hp_bonus, d.max_hp, d.hp) == (100, 10, 110, 100)
        b.end_spell(second.id)
        assert (d.base_max_hp, d.spell_hp_bonus, d.max_hp, d.hp) == (100, 5, 105, 95)
        b.end_spell(first.id)
        assert (d.base_max_hp, d.spell_hp_bonus, d.max_hp, d.hp) == (100, 0, 100, 90)
    oracle()
    mutation_fails(monkeypatch, SpellMechanics, 'restore',
                   'target.base_max_hp = target.original_max_hp', 'target.max_hp = target.original_max_hp', oracle)
    mutation_fails(monkeypatch, Combat, 'refresh_spell_effects',
                   'actor.spell_hp_bonus = bonus', 'actor.max_hp += delta\n        actor.spell_hp_bonus = bonus', oracle)

def test_step3_fix2_D_dispel_registers_all_participants(monkeypatch):
    def oracle():
        for end_on in ['caster', 'recipient']:
            b, c, (d, other) = arena('Warding Bond', enemies=2)
            bond = b.cast(c, 'Warding Bond', [d])
            assert bond.affected == {'main': {c, d}}
            other.spells = ['Dispel Magic']; other.spell_slots = {3: 2}
            b.begin_turn(other); b.cast(other, 'Dispel Magic', [other], slot=3)
            assert bond.active and bond.affected == {'main': {c, d}}
            hp = (c.hp, d.hp)
            b.damage(d, 10, 'fire')
            assert (c.hp, d.hp) == (hp[0] - 5, hp[1] - 5)
            b.begin_turn(other)
            dispel = b.cast(other, 'Dispel Magic', [c if end_on == 'caster' else d], slot=3)
            assert dispel is not None
            assert not bond.active and bond.affected == {}
            assert not any(e.source == bond.id for a in b.combatants for e in a.effects)
            assert [e['spell'] for e in b.log if e['event'] == 'dispel'] == ['Warding Bond']
            hp = (c.hp, d.hp)
            b.damage(d, 10, 'fire')
            assert (c.hp, d.hp) == (hp[0], hp[1] - 10)
    oracle()
    mutation_fails(monkeypatch, Combat, 'execute',
                   '*(ctx[name] for name in primitive.get("participants", []))', '*()', oracle)
    import pytest
    primitive = next(p for p in spell_specs()['Warding Bond']['effects'][0]['apply'] if 'bond' in p)
    with monkeypatch.context() as patch:
        patch.delitem(primitive, 'participants')
        with pytest.raises(AssertionError): oracle()

def test_step3_fix2_E_conditional_saves_apply_without_a_roll(monkeypatch):
    def oracle():
        from test_engine_step3_damage import BalancedRolls
        conditional = {(s['name'], block['id']): block['save']['if']
                       for s in spell_specs().values() for block in s['effects']
                       if block['save'] and 'if' in block['save']}
        assert conditional == {('Enlarge/Reduce', 'main'): 'not target.willing',
                               ('Dispel Evil and Good', 'function'): '$function == dismiss'}
        for mode in ['enlarge', 'reduce']:
            for recipient in ['willing_caster', 'willing_other', 'failed_save', 'successful_save']:
                b, c, (d,) = arena('Enlarge/Reduce', enemies=1)
                b.rng = BalancedRolls(10, False)
                target = c if recipient == 'willing_caster' else d
                target.willing = recipient.startswith('willing')
                target.save_bonuses['con'] = 100 if recipient == 'successful_save' else -100
                inst = b.cast(c, 'Enlarge/Reduce', [target], choices={'size': mode})
                assert inst is not None
                applied = recipient != 'successful_save'
                assert target.size == (('L' if mode == 'enlarge' else 'S') if applied else 'M')
                flags = (mode == 'enlarge', mode == 'reduce') if applied else (False, False)
                assert b.roll_flags(target, 'ability_checks', 'str') == flags
                assert b.roll_flags(target, 'saves', 'str') == flags
                assert b.roll_flags(target, 'saves', 'dex') == (False, False)
                saves = [e for e in b.log if e['event'] == 'save']
                assert len(saves) == (0 if target.willing else 1)
                if saves: assert saves[0]['success'] is (not applied)
                victim = d if target is c else c
                hp = victim.hp
                b.weapon_attack(target, victim, {'name': 'Probe', 'kind': 'melee', 'to_hit': 100,
                    'effects': [{'damage': {'amount': 5, 'type': 'bludgeoning'}}]})
                assert hp - victim.hp == ((6 if mode == 'enlarge' else 4) if applied else 5)
                b.end_spell(inst.id)
                assert target.size == 'M'
                assert b.roll_flags(target, 'saves', 'str') == (False, False)
                assert not any(e.kind == 'weapon_adjustment' for e in target.active_effects)
        # The other conditional-save spell deliberately has a different apply branch.
        b, c, (d,) = arena('Dispel Evil and Good', enemies=1)
        c.creature_type = 'fiend'; c.spells.append('Charm Person')
        charm = b.cast(c, 'Charm Person', [d])
        assert charm is not None and d.has_condition('charmed')
        b.begin_turn(c); inst = b.cast(c, 'Dispel Evil and Good', choices={'function': 'break'})
        b.begin_turn(c); b.log.clear()
        assert b.command(inst, 'action_command', [d])
        assert not d.has_condition('charmed') and d.alive and not d.removed
        assert not inst.active and c.concentration is None
        assert not any(e['event'] == 'save' for e in b.log)
    oracle()
    mutation_fails(monkeypatch, Combat, 'resolve_block',
                   'if block["save"] and not primitives:', 'if False:', oracle)
    mutation_fails(monkeypatch, Combat, 'resolve_block',
                   'primitives = block["apply"]', 'primitives = block["on_fail"] if block["save"] else block["apply"]', oracle)

def test_step3_fix2_F_continuous_source_specific_condition_riders(monkeypatch):
    from test_engine_step3 import cast_fixture
    from test_engine_step3_damage import BalancedRolls
    import pytest

    def audit():
        dependencies = {}
        for name, spec in spell_specs().items():
            for block in spec['effects']:
                if block.get('requires_condition'):
                    dependencies[(name, block['id'], 'block')] = block['requires_condition']
                for branch in ['apply', 'on_fail', 'on_success', 'on_hit']:
                    for index, primitive in enumerate(block[branch]):
                        if primitive.get('requires_condition'):
                            dependencies[(name, block['id'], branch, index)] = primitive['requires_condition']
        assert len(spell_specs()) == 273  # 245 level 0-5 specs plus the level 6-9 batch (engine/spell_high.py)
        assert dependencies == {
            ('Contagion', 'main', 'on_fail', 2): 'poisoned',
            ('Stinking Cloud', 'main', 'on_fail', 1): 'poisoned',
            ('Ensnaring Strike', 'vines', 'apply', 0): 'restrained',
            ("Bigby's Hand", 'crush', 'block'): 'grappled',
            ('Conjure Elemental', 'hold', 'block'): 'restrained',
            ('Suggestion', 'main', 'on_fail', 1): 'charmed',
            ('Crown of Madness', 'main', 'on_fail', 1): 'charmed',
            ('Hypnotic Pattern', 'main', 'on_fail', 1): 'charmed',
            ('Hypnotic Pattern', 'main', 'on_fail', 2): 'charmed',
            ('Modify Memory', 'main', 'on_fail', 1): 'charmed',
            ("Otto's Irresistible Dance", 'main', 'on_fail', 1): 'charmed',
            ("Otto's Irresistible Dance", 'main', 'on_fail', 2): 'charmed',
            ("Otto's Irresistible Dance", 'main', 'on_fail', 3): 'charmed',
        }
        # The remaining condition predicate in embedded spell stat blocks is
        # Putrid Spirit's paralysis *application* prerequisite, not its duration.
        def predicates(value, path=()):
            if isinstance(value, dict):
                for k, v in value.items(): yield from predicates(v, path + (k,))
            elif isinstance(value, list):
                for i, v in enumerate(value): yield from predicates(v, path + (i,))
            elif isinstance(value, str) and 'has_condition' in value: yield path, value
        remaining = {(n, value) for n, spec in spell_specs().items() for _, value in predicates(spec)}
        assert remaining == {
            ("Bigby's Hand", 'target.has_condition_from(grappled, spell)'),
            ('Conjure Elemental', 'not target.has_condition_from(restrained, spell)'),
            ('Summon Undead', 'target.has_condition(poisoned)'),
        }

    def poison_oracle():
        for remove in [False, True]:
            b, c, (d, other) = arena('Contagion', enemies=2)
            b.rng = BalancedRolls(10, False)
            inst = b.cast(c, 'Contagion', [d], choices={'ability': 'wis'})
            assert d.has_condition('poisoned')
            assert b.roll_flags(d, 'saves', 'wis') == (False, True)
            assert b.roll_flags(d, 'saves', 'dex') == (False, False)
            rider = next(e for e in d.effects if e.kind == 'disadvantage')
            condition = next(e for e in d.effects if e.kind == 'apply_condition')
            assert rider.requires_condition == 'poisoned' and rider.source == inst.id
            condition.suppressed = True
            assert not d.has_condition('poisoned') and b.roll_flags(d, 'saves', 'wis') == (False, False)
            condition.suppressed = False
            assert b.roll_flags(d, 'saves', 'wis') == (False, True)
            other.spells = ['Feign Death']; other.spell_slots = {3: 1}
            b.begin_turn(other); feign = b.cast(other, 'Feign Death', [d])
            assert feign is not None and not d.has_condition('poisoned')
            assert rider in d.effects and b.roll_flags(d, 'saves', 'wis') == (False, False)
            # A rider registered while its condition is ineffective must persist
            # dormant, not be skipped forever at application time.
            d.effects.remove(rider)
            declaration = inst.spec['effects'][0]['on_fail'][2]
            b.execute(inst, d, [declaration], b.context(inst, d), 'main')
            assert b.roll_flags(d, 'saves', 'wis') == (False, False)
            b.end_spell(feign.id)
            assert d.has_condition('poisoned') and b.roll_flags(d, 'saves', 'wis') == (False, True)
            if remove:
                d.save_bonuses['con'] = 100
                b.restore(d, 'poisoned')
            else:
                b.remove_effects(inst, d)
            assert not d.has_condition('poisoned') and b.roll_flags(d, 'saves', 'wis') == (False, False)
            d.effects.append(Effect('apply_condition', {'condition': 'poisoned', 'caster_id': c.id}, 999, 'foreign'))
            assert d.has_condition('poisoned') and b.roll_flags(d, 'saves', 'wis') == (False, False)

    def cloud_oracle():
        b, c, (d,) = arena('Stinking Cloud', enemies=1)
        b.area = lambda *_: [1]; inst = b.cast(c, 'Stinking Cloud')
        b.begin_turn(d)
        assert d.has_condition('poisoned') and b.turn_rules(d).get('no_action')
        assert (d.action, d.bonus_action) == (0, 0)
        immunity = Effect('defense', {'condition_immunity': ['poisoned']}, 999, 'immune')
        d.effects.append(immunity); b.refresh_spell_effects()
        assert not d.has_condition('poisoned') and b.turn_rules(d) == {}
        assert (d.action, d.bonus_action) == (1, 1)
        d.effects.remove(immunity); b.refresh_spell_effects()
        assert d.has_condition('poisoned') and b.turn_rules(d).get('no_bonus_action')
        assert (d.action, d.bonus_action) == (0, 0)
        b.restore(d, 'poisoned')
        d.effects.append(Effect('apply_condition', {'condition': 'poisoned', 'caster_id': c.id}, 999, 'foreign'))
        assert d.has_condition('poisoned') and b.turn_rules(d) == {}
        assert (d.action, d.bonus_action) == (1, 1)
        b.spend_economy(d, 'action')
        d.effects.append(Effect('apply_condition', {'condition': 'poisoned', 'magical': True}, inst.id, 'main'))
        b.refresh_spell_effects()
        assert (d.action, d.bonus_action) == (0, 0)
        b.restore(d, 'poisoned')
        assert (d.action, d.bonus_action) == (0, 1)  # No refund of a spent action.
        b.end_turn(d)
        assert not any(e.source == inst.id for e in d.effects)

    def recurring_oracle():
        b, c, (d,) = arena('Ensnaring Strike', enemies=1)
        b.rng = BalancedRolls(10, False)
        inst = cast_fixture(b, c, 'Ensnaring Strike')
        assert inst.active and d.has_condition('restrained')
        hp = d.hp; b.begin_turn(d)
        assert d.hp == hp - 1
        defense = Effect('defense', {'magical_condition_immunity': ['restrained']}, 999, 'immune')
        d.effects.append(defense)
        hp = d.hp; b.begin_turn(d)
        assert not d.has_condition('restrained') and d.hp == hp
        d.effects.remove(defense)
        b.begin_turn(d)
        assert d.has_condition('restrained') and d.hp == hp - 1
        b.restore(d, 'restrained')
        d.effects.append(Effect('apply_condition', {'condition': 'restrained', 'caster_id': c.id}, 999, 'foreign'))
        hp = d.hp; b.begin_turn(d)
        assert inst.active and d.has_condition('restrained') and d.hp == hp
        for name, block_id, condition, expected in [
                ("Bigby's Hand", 'crush', 'grappled', 8),
                ('Conjure Elemental', 'hold', 'restrained', 4)]:
            b, c, (d,) = arena(name, enemies=1); b.rng = BalancedRolls(10, False)
            inst = b.cast(c, name, [d], choices={'mode': 'grasp'} if block_id == 'crush' else {'type': 'fire'})
            if block_id == 'hold':
                d.effects.append(Effect('apply_condition', {'condition': condition, 'caster_id': c.id, 'magical': True}, inst.id, 'catch'))
            else: inst.choices['mode'] = 'crush'
            block = deepcopy(next(x for x in inst.spec['effects'] if x['id'] == block_id))
            # Isolate the block's dependency from Bigby's extra selection filter.
            block['target'].pop('eligible_if', None)
            event = 'bonus_action_command' if block_id == 'crush' else 'start_of_turn'
            hp = d.hp
            assert b.resolve_block(inst, block, event, {'who': d}, [d])
            assert d.hp == hp - expected
            defense = Effect('defense', {'condition_immunity': [condition]}, 999, 'immune')
            d.effects.append(defense); b.turn_index += 1; b.log.clear(); hp = d.hp
            assert not b.resolve_block(inst, block, event, {'who': d}, [d])
            assert d.hp == hp and not any(e['event'] == 'save' for e in b.log)
            d.effects.remove(defense); b.turn_index += 1
            assert b.resolve_block(inst, block, event, {'who': d}, [d])
            assert d.hp == hp - expected
            b.restore(d, condition)
            d.effects.append(Effect('apply_condition', {'condition': condition, 'caster_id': c.id}, 999, 'foreign'))
            b.turn_index += 1; hp = d.hp
            assert d.has_condition_from(condition, c) and not d.has_condition_from(condition, inst)
            assert not b.resolve_block(inst, block, event, {'who': d}, [d])
            assert d.hp == hp

    audit(); poison_oracle(); cloud_oracle(); recurring_oracle()
    mutation_fails(monkeypatch, Combat, 'execute',
                   'effect.requires_condition = primitive.get("requires_condition")',
                   'effect.requires_condition = None', poison_oracle)
    mutation_fails(monkeypatch, Combatant, 'has_condition_source',
                   'e.source == source and', 'True and', poison_oracle)
    mutation_fails(monkeypatch, Combatant, 'has_condition_source',
                   'and self.condition_effective(e, active)', '', poison_oracle)
    mutation_fails(monkeypatch, Combat, 'execute',
                   'if key in INSTANT_PRIMITIVES and primitive.get("requires_condition")',
                   'if False and key in INSTANT_PRIMITIVES and primitive.get("requires_condition")', recurring_oracle)
    mutation_fails(monkeypatch, Combat, 'resolve_block',
                   'if block.get("requires_condition"):', 'if False:', recurring_oracle)
    mutation_fails(monkeypatch, Combat, 'reconcile_economy',
                   'getattr(actor, kind) + actor.blocked_economy.pop(kind)',
                   'getattr(actor, kind) + 0 * actor.blocked_economy.pop(kind)', cloud_oracle)
    for name, block_id, branch, index in [('Contagion', 'main', 'on_fail', 2),
                                         ('Stinking Cloud', 'main', 'on_fail', 1),
                                         ('Ensnaring Strike', 'vines', 'apply', 0)]:
        block = next(b for b in spell_specs()[name]['effects'] if b['id'] == block_id)
        with monkeypatch.context() as patch:
            patch.delitem(block[branch][index], 'requires_condition')
            with pytest.raises(AssertionError): audit()
