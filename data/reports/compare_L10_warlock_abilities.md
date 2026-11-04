# Build comparison: warlock, level 10

Each row swaps the candidate into the reference party in place of its wizard and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex | 2,383 | yes |
| 14 Con, 13 Wis | 2,383 | yes |
| 14 Con, 13 Dex; ASI con first | 2,319 | yes |
| 14 Con, 13 Wis; ASI con first | 2,319 | yes |
| standard | 2,257 | yes |
| 14 Dex, 13 Wis | 2,257 | yes |
| 14 Dex, 13 Con; ASI split | 2,229 | no |
| 14 Dex, 13 Wis; ASI con first | 2,229 | no |
| 14 Wis, 13 Con | 2,096 | no |
| 14 Con, 13 Dex; ASI split | 2,070 | no |
| 14 Con, 13 Wis; ASI split | 2,070 | no |
| 14 Wis, 13 Con; ASI split | 2,070 | no |
| 14 Dex, 13 Wis; ASI split | 1,961 | no |
| 14 Wis, 13 Dex; ASI split | 1,821 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Wis; ASI con first | +6% (0.77×) | +1% ≈ | +1% ≈ | +23% | +2% ≈ | +10% ≈ | -0% ≈ |
| 14 Con, 13 Dex; ASI con first | +6% (0.77×) | +1% ≈ | +1% ≈ | +23% | +2% ≈ | +10% ≈ | -0% ≈ |
| 14 Con, 13 Dex | +6% (0.77×) | +5% ≈ | +1% ≈ | +25% | +1% ≈ | +4% ≈ | +0% ≈ |
| 14 Con, 13 Wis | +6% (0.77×) | +5% ≈ | +1% ≈ | +25% | +1% ≈ | +4% ≈ | +0% ≈ |
| standard | +4% (0.76×) | +0% ≈ | +2% ≈ | +23% | +1% ≈ | +2% ≈ | -1% ≈ |
| 14 Dex, 13 Wis | +4% (0.76×) | +0% ≈ | +2% ≈ | +23% | +1% ≈ | +2% ≈ | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
