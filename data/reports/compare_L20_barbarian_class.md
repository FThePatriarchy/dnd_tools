# Build comparison: barbarian, level 20

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v2 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Reference party: standard (fighter_20, cleric_20, rogue_20, wizard_20)

Base rating 44,105 XP (0.50× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| barbarian_20 | -8% (0.46×) | +6% ≈ | +5% ≈ | +19% | +2% ≈ | -34% | -32% |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
