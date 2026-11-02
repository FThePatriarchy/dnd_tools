# Build comparison: fighter, level 10

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| standard | 4,576 | yes |
| 14 Con, 13 Dex; ASI con first | 4,436 | yes |
| 14 Dex, 13 Con | 4,136 | yes |
| 14 Wis, 13 Con | 4,136 | yes |
| 14 Dex, 13 Con; ASI con first | 4,047 | yes |
| 14 Wis, 13 Con; ASI con first | 4,047 | yes |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Dex; ASI con first | +0% ≈ (0.73×) | +2% ≈ | +1% ≈ | +2% ≈ | -1% ≈ | -2% ≈ | +0% ≈ |
| standard | +0% ≈ (0.73×) | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ | +0% ≈ |
| 14 Wis, 13 Con; ASI con first | -0% ≈ (0.73×) | +2% ≈ | +1% ≈ | -1% ≈ | -2% ≈ | -2% ≈ | +1% ≈ |
| 14 Dex, 13 Con; ASI con first | -0% ≈ (0.73×) | +3% ≈ | +1% ≈ | +0% ≈ | -5% ≈ | -0% ≈ | +0% ≈ |
| 14 Wis, 13 Con | -0% ≈ (0.73×) | +1% ≈ | -0% ≈ | -1% ≈ | -0% ≈ | -1% ≈ | +0% ≈ |
| 14 Dex, 13 Con | -1% ≈ (0.73×) | +0% ≈ | +0% ≈ | -1% ≈ | -1% ≈ | -2% ≈ | +0% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
