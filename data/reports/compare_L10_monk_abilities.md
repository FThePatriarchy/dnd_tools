# Build comparison: monk, level 10

Each row swaps the candidate into the reference party in place of its rogue and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Wis | 2,103 | yes |
| 14 Con, 13 Str | 2,103 | yes |
| standard | 2,017 | yes |
| 14 Wis, 13 Str | 2,017 | yes |
| 14 Str, 13 Wis | 1,849 | yes |
| 14 Con, 13 Wis; ASI con first | 1,824 | yes |
| 14 Con, 13 Str; ASI con first | 1,824 | no |
| 14 Wis, 13 Con; ASI split | 1,764 | no |
| 14 Wis, 13 Str; ASI con first | 1,764 | no |
| 14 Con, 13 Wis; ASI split | 1,628 | no |
| 14 Con, 13 Str; ASI split | 1,628 | no |
| 14 Str, 13 Wis; ASI con first | 1,628 | no |
| 14 Wis, 13 Str; ASI split | 1,551 | no |
| 14 Str, 13 Wis; ASI split | 1,432 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Wis | +7% (0.78×) | +22% | +1% ≈ | +8% ≈ | +3% ≈ | +7% ≈ | +2% ≈ |
| 14 Con, 13 Str | +7% (0.78×) | +22% | +1% ≈ | +8% ≈ | +3% ≈ | +7% ≈ | +2% ≈ |
| 14 Str, 13 Wis | +6% (0.77×) | +18% | -0% ≈ | +4% ≈ | +4% ≈ | +9% ≈ | +2% ≈ |
| 14 Con, 13 Wis; ASI con first | +6% (0.77×) | +15% | +0% ≈ | +6% ≈ | +5% ≈ | +8% ≈ | +2% ≈ |
| standard | +5% (0.77×) | +14% | -0% ≈ | +6% ≈ | +3% ≈ | +8% ≈ | +3% ≈ |
| 14 Wis, 13 Str | +5% (0.77×) | +14% | -0% ≈ | +6% ≈ | +3% ≈ | +8% ≈ | +3% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
