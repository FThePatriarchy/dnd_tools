# Build comparison: ranger, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 1,300 | yes |
| standard | 1,060 | yes |
| feat: alert | 1,060 | yes |
| feat: lucky | 1,060 | yes |
| feat: sharpshooter | 1,060 | yes |
| feat: resilient | 812 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: lucky | -7% (0.74×) | -7% ≈ | -8% ≈ | -21% | -2% ≈ | -3% ≈ | +4% ≈ |
| feat: tough | -7% (0.74×) | -5% ≈ | -9% ≈ | -18% | -1% ≈ | -12% | +5% ≈ |
| feat: resilient | -7% (0.74×) | -7% ≈ | -9% ≈ | -22% | -2% ≈ | -5% ≈ | +5% ≈ |
| standard | -8% (0.74×) | -6% ≈ | -10% ≈ | -19% | -2% ≈ | -12% | +4% ≈ |
| feat: sharpshooter | -8% (0.74×) | -6% ≈ | -10% ≈ | -19% | -2% ≈ | -12% | +4% ≈ |
| feat: alert | -8% (0.73×) | -9% ≈ | -10% ≈ | -21% | -3% ≈ | -8% ≈ | +2% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
