from src.battle.engine import BattleEngine, Creature, Move


class StaticRNG:
    def __init__(self, uniform_value=1.0):
        self.uniform_value = uniform_value

    def uniform(self, _low, _high):
        return self.uniform_value

    def choice(self, items):
        return list(items)[0]


def _make_creature(name, type_, hp=100, attack=60, defense=50, moves=None):
    if moves is None:
        moves = []
    creature = Creature(
        name=name,
        type_=type_,
        max_hp=hp,
        attack=attack,
        defense=defense,
        moves=moves,
        sprite=None,
        base_stats={"max_hp": hp, "attack": attack, "defense": defense},
    )
    creature.current_hp = hp
    return creature


def test_engine_player_turn_damage_and_win_transition():
    finishing_move = Move("Finisher", "Fire", 100)
    player = _make_creature("PlayerMon", "Fire", hp=120, attack=90, defense=50, moves=[finishing_move])
    opponent = _make_creature("OppMon", "Nature", hp=10, attack=40, defense=30, moves=[Move("Scratch", "Normal", 10)])

    engine = BattleEngine(player, opponent, type_chart={"Fire": {"Nature": 2.0}}, rng=StaticRNG(uniform_value=1.0))
    result = engine.resolve_player_turn(finishing_move)

    assert result.damage > 0
    assert result.defender_fainted is True
    assert result.winner == "player"
    assert engine.winner == "player"
    assert opponent.current_hp == 0


def test_engine_stat_move_produces_stat_event():
    stat_move = Move("Focus", "Normal", 0, effect={"target": "self", "stat": "attack", "change": 1})
    player = _make_creature("PlayerMon", "Normal", hp=100, attack=40, defense=50, moves=[stat_move])
    opponent = _make_creature("OppMon", "Normal", hp=100, attack=40, defense=50, moves=[Move("Hit", "Normal", 20)])

    engine = BattleEngine(player, opponent, type_chart={}, rng=StaticRNG(uniform_value=1.0))
    before_attack = player.attack
    result = engine.resolve_player_turn(stat_move)

    assert result.damage == 0
    assert result.effectiveness == 1
    assert len(result.stat_events) == 1
    assert result.stat_events[0]["kind"] == "stat_change"
    assert result.stat_events[0]["stat"] == "attack"
    assert result.stat_events[0]["before"] == before_attack
    assert result.stat_events[0]["after"] == player.attack
    assert player.attack > before_attack
    assert engine.turn == "opponent"
    assert engine.winner is None


def test_engine_round_resolves_to_opponent_win():
    weak_move = Move("Weak Tap", "Normal", 1)
    strong_move = Move("Big Hit", "Normal", 120)
    player = _make_creature("PlayerMon", "Normal", hp=25, attack=20, defense=20, moves=[weak_move])
    opponent = _make_creature("OppMon", "Normal", hp=100, attack=90, defense=20, moves=[strong_move])

    engine = BattleEngine(player, opponent, type_chart={"Normal": {"Normal": 1.0}}, rng=StaticRNG(uniform_value=1.0))
    results = engine.resolve_round(player_move=weak_move, opponent_move=strong_move)

    assert len(results) == 2
    assert results[0].actor == "player"
    assert results[1].actor == "opponent"
    assert results[1].winner == "opponent"
    assert engine.winner == "opponent"
    assert player.current_hp == 0
