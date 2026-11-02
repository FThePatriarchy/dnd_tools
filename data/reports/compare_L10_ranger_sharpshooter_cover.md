# Build comparison: ranger, level 10

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing. Cover and ranged-in-melee rules on (`DayOptions.cover`).

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,113 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| archer + sharpshooter | -12% (0.64×) | -6% ≈ | -1% ≈ | -3% ≈ | -21% | -35% | -2% ≈ |
| standard | -13% (0.64×) | -6% ≈ | -1% ≈ | -3% ≈ | -21% | -35% | -2% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
