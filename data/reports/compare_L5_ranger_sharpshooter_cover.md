# Build comparison: ranger, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing. Cover and ranged-in-melee rules on (`DayOptions.cover`).

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,517 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| archer + sharpshooter | -8% (0.74×) | -7% ≈ | -10% ≈ | -19% | -2% ≈ | -11% | +4% ≈ |
| standard | -8% (0.74×) | -8% ≈ | -10% ≈ | -19% | -2% ≈ | -11% | +4% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
