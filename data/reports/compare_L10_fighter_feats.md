# Build comparison: fighter, level 10

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 5,456 | yes |
| standard | 4,576 | yes |
| feat: alert | 4,576 | yes |
| feat: lucky | 4,576 | yes |
| feat: great weapon master | 4,136 | yes |
| feat: resilient | 4,136 | yes |
| feat: polearm master | 3,483 | yes |
| feat: polearm master + great weapon master | 3,483 | yes |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,065 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: great weapon master | +4% (0.76×) | +14% | +2% ≈ | +7% ≈ | +0% ≈ | +1% ≈ | -0% ≈ |
| feat: lucky | +3% (0.75×) | +10% ≈ | +3% ≈ | +8% ≈ | +0% ≈ | -1% ≈ | +0% ≈ |
| feat: alert | +2% ≈ (0.74×) | +7% ≈ | -1% ≈ | +0% ≈ | -0% ≈ | +4% ≈ | +1% ≈ |
| feat: polearm master + great weapon master | +1% ≈ (0.74×) | +6% ≈ | +3% ≈ | +1% ≈ | -1% ≈ | +1% ≈ | -0% ≈ |
| feat: tough | +1% ≈ (0.74×) | +2% ≈ | +2% ≈ | +2% ≈ | +1% ≈ | -1% ≈ | -0% ≈ |
| standard | +0% ≈ (0.73×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |
| feat: resilient | -0% ≈ (0.73×) | +1% ≈ | -0% ≈ | -1% ≈ | -0% ≈ | -1% ≈ | -0% ≈ |
| feat: polearm master | -1% ≈ (0.72×) | +0% ≈ | -1% ≈ | -1% ≈ | -1% ≈ | -3% ≈ | -0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
