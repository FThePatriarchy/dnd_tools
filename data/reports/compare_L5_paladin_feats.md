# Build comparison: paladin, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| feat: tough | 1,816 | yes |
| standard | 1,480 | yes |
| feat: alert | 1,480 | yes |
| feat: lucky | 1,480 | yes |
| feat: great weapon master | 1,480 | yes |
| feat: resilient | 1,408 | yes |
| feat: polearm master | 1,300 | yes |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feat: tough | +0% ≈ (0.80×) | +5% ≈ | -0% ≈ | -5% ≈ | +1% ≈ | -6% ≈ | +6% ≈ |
| feat: lucky | -0% ≈ (0.80×) | -1% ≈ | -0% ≈ | -5% ≈ | +0% ≈ | +1% ≈ | +5% ≈ |
| feat: great weapon master | -1% ≈ (0.79×) | -0% ≈ | +1% ≈ | -6% ≈ | +2% ≈ | -7% ≈ | +4% ≈ |
| feat: resilient | -1% ≈ (0.79×) | +2% ≈ | -4% ≈ | -12% | +1% ≈ | +2% ≈ | +4% ≈ |
| standard | -2% ≈ (0.78×) | -0% ≈ | -2% ≈ | -7% ≈ | +2% ≈ | -6% ≈ | +4% ≈ |
| feat: alert | -3% ≈ (0.78×) | +1% ≈ | -7% ≈ | -13% | -0% ≈ | +0% ≈ | +5% ≈ |
| feat: polearm master | -3% (0.77×) | +1% ≈ | -1% ≈ | -17% | +0% ≈ | -6% ≈ | +6% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
