# Build comparison: sorcerer, level 10

Each row swaps the candidate into the reference party in place of its wizard and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex | 1,749 | yes |
| 14 Con, 13 Wis | 1,749 | yes |
| standard | 1,676 | yes |
| 14 Dex, 13 Wis | 1,676 | yes |
| 14 Con, 13 Dex; ASI con first | 1,592 | yes |
| 14 Con, 13 Wis; ASI con first | 1,592 | yes |
| 14 Dex, 13 Con; ASI split | 1,538 | no |
| 14 Dex, 13 Wis; ASI con first | 1,538 | no |
| 14 Wis, 13 Con | 1,536 | no |
| 14 Con, 13 Dex; ASI split | 1,419 | no |
| 14 Con, 13 Wis; ASI split | 1,419 | no |
| 14 Wis, 13 Con; ASI split | 1,419 | no |
| 14 Dex, 13 Wis; ASI split | 1,350 | no |
| 14 Wis, 13 Dex; ASI split | 1,246 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| standard | +12% (0.82×) | +21% | +4% ≈ | +25% | +23% | +4% ≈ | +0% ≈ |
| 14 Dex, 13 Wis | +12% (0.82×) | +21% | +4% ≈ | +25% | +23% | +4% ≈ | +0% ≈ |
| 14 Con, 13 Wis | +12% (0.82×) | +18% | +8% ≈ | +29% | +17% | +3% ≈ | +0% ≈ |
| 14 Con, 13 Dex | +12% (0.82×) | +18% | +8% ≈ | +29% | +17% | +3% ≈ | +0% ≈ |
| 14 Con, 13 Dex; ASI con first | +11% (0.81×) | +19% | -0% ≈ | +32% | +12% | +6% ≈ | -0% ≈ |
| 14 Con, 13 Wis; ASI con first | +11% (0.81×) | +19% | -0% ≈ | +32% | +12% | +6% ≈ | -0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
