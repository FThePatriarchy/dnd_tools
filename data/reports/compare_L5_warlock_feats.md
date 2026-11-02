# Build comparison: warlock, level 5

Each row swaps the candidate into the reference party in place of its wizard and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 1,276 | yes |
| standard | 1,010 | yes |
| feat: alert | 1,010 | yes |
| feat: lucky | 1,010 | yes |
| feat: war caster | 1,010 | yes |
| feat: resilient | 867 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: lucky | -21% (0.63×) | +0% ≈ | +4% ≈ | +5% ≈ | -2% ≈ | +0% ≈ | -77% |
| feat: tough | -22% (0.63×) | +5% ≈ | +5% ≈ | +4% ≈ | -0% ≈ | -9% ≈ | -78% |
| feat: alert | -23% (0.61×) | +0% ≈ | -7% ≈ | -1% ≈ | -2% ≈ | -6% ≈ | -76% |
| standard | -23% (0.61×) | -1% ≈ | -2% ≈ | +3% ≈ | -1% ≈ | -9% ≈ | -78% |
| feat: war caster | -23% (0.61×) | -1% ≈ | -2% ≈ | +3% ≈ | -1% ≈ | -9% ≈ | -78% |
| feat: resilient | -25% (0.60×) | -5% ≈ | -6% ≈ | -1% ≈ | -2% ≈ | -6% ≈ | -78% |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
