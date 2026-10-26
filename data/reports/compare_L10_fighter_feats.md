# Build comparison: fighter, level 10

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,065 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: great weapon master | +4% (0.76×) | +14% | +2% ≈ | +7% ≈ | +0% ≈ | +1% ≈ | -0% ≈ |
| feat: alert | +2% ≈ (0.74×) | +7% ≈ | -1% ≈ | +0% ≈ | -0% ≈ | +4% ≈ | +1% ≈ |
| standard | +0% ≈ (0.73×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
