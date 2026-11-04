# Build comparison: paladin, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Cha; ASI split | 1,648 | yes |
| standard | 1,480 | yes |
| 14 Cha, 13 Con | 1,480 | yes |
| 14 Wis, 13 Con | 1,480 | yes |
| 14 Con, 13 Cha; ASI con first | 1,408 | yes |
| 14 Cha, 13 Con; ASI con first | 1,408 | yes |
| 14 Wis, 13 Con; ASI con first | 1,408 | no |
| 14 Cha, 13 Wis | 1,312 | no |
| 14 Wis, 13 Cha | 1,312 | no |
| 14 Cha, 13 Wis; ASI con first | 1,264 | no |
| 14 Wis, 13 Cha; ASI con first | 1,264 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Cha; ASI split | +0% ≈ (0.80×) | +6% ≈ | -0% ≈ | -4% ≈ | +1% ≈ | -6% ≈ | +5% ≈ |
| 14 Cha, 13 Con; ASI con first | -1% ≈ (0.79×) | +2% ≈ | -2% ≈ | -4% ≈ | +2% ≈ | -6% ≈ | +4% ≈ |
| 14 Con, 13 Cha; ASI con first | -1% ≈ (0.79×) | +2% ≈ | -2% ≈ | -5% ≈ | +1% ≈ | -3% ≈ | +4% ≈ |
| 14 Cha, 13 Con | -1% ≈ (0.79×) | -0% ≈ | -1% ≈ | -3% ≈ | +1% ≈ | -6% ≈ | +3% ≈ |
| 14 Wis, 13 Con | -2% ≈ (0.78×) | -0% ≈ | -2% ≈ | -7% ≈ | +2% ≈ | -6% ≈ | +4% ≈ |
| standard | -2% ≈ (0.78×) | -0% ≈ | -2% ≈ | -7% ≈ | +2% ≈ | -6% ≈ | +4% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
