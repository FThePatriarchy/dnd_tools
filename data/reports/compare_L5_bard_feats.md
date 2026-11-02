# Build comparison: bard, level 5

Each row swaps the candidate into the reference party in place of its cleric and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 463 | yes |
| standard | 366 | yes |
| feat: alert | 366 | yes |
| feat: lucky | 366 | yes |
| feat: war caster | 366 | yes |
| feat: resilient | 342 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: alert | +2% ≈ (0.82×) | +6% ≈ | -6% ≈ | -3% ≈ | -3% ≈ | +24% | -1% ≈ |
| feat: tough | +2% ≈ (0.81×) | +5% ≈ | -4% ≈ | -2% ≈ | -2% ≈ | +17% | -1% ≈ |
| standard | +2% ≈ (0.81×) | +4% ≈ | -4% ≈ | -2% ≈ | -2% ≈ | +17% | -1% ≈ |
| feat: lucky | +2% ≈ (0.81×) | +4% ≈ | -3% ≈ | -1% ≈ | -2% ≈ | +16% | -2% ≈ |
| feat: war caster | +2% ≈ (0.81×) | +5% ≈ | -4% ≈ | -2% ≈ | -2% ≈ | +16% | -1% ≈ |
| feat: resilient | +0% ≈ (0.80×) | -1% ≈ | -3% ≈ | -9% ≈ | -3% ≈ | +21% | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
