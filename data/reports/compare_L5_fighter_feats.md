# Build comparison: fighter, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: alert | +4% (0.83×) | +2% ≈ | +5% ≈ | -2% ≈ | +4% ≈ | +13% | -1% ≈ |
| feat: great weapon master | +4% (0.83×) | -0% ≈ | +6% ≈ | -0% ≈ | +3% ≈ | +12% | +2% ≈ |
| standard | +0% ≈ (0.80×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
