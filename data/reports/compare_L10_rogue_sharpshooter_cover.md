# Build comparison: rogue, level 10

Each row swaps the candidate into the reference party in place of its rogue and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing. Cover and ranged-in-melee rules on (`DayOptions.cover`).

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 8,645 XP (0.70× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| archer, no feat | +1% ≈ (0.70×) | +3% ≈ | -1% ≈ | +4% ≈ | +0% ≈ | -1% ≈ | +0% ≈ |
| archer + sharpshooter | +0% ≈ (0.70×) | +2% ≈ | -2% ≈ | +4% ≈ | +0% ≈ | -3% ≈ | +0% ≈ |
| standard | +0% ≈ (0.70×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
