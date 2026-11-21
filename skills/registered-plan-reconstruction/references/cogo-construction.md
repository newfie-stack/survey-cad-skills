# Deterministic COGO construction
## Bearing-distance
For azimuth measured clockwise from grid north, use ΔE = d sin(azimuth) and ΔN = d cos(azimuth); E2=E1+ΔE, N2=N1+ΔN. Convert quadrant bearings explicitly and verify the bearing basis.
## Offsets and intersections
For segment A→B, unit tangent t=(dx/L,dy/L). Left normal n=(-dy/L,dx/L), right normal -n. Offset a straight segment by signed perpendicular width w. At deflections, intersect the infinite offset lines analytically; detect near-parallel cases, reversals and excessive miters.
## Road limits and terminals
Retain the full controlling survey course. Solve each R/W side against its independently established terminal line. Do not use a tie line as a terminal. Check road allowance width from applicable survey evidence; nominal 20.12 m is not universal.
## Grid/ground
Record the plan's bearing basis, units, coordinate reference system and any stated combined factor. For ordinary local reconstruction, use printed bearings, distances and widths as recorded; keep a combined factor as metadata. If a separate, explicitly requested and justified transformation uses a factor, record its direction, applicability and checked residuals, and never change the stored printed observations or the accepted local reconstruction. Raster axes are for interpretation only; normalize the image's downward Y axis for comparison and verify orientation independently. This is not a scale or reflection of the legal geometry.
## Validation
Recompute printed distances/bearings from coordinates, polygon closure vector and linear misclosure, area by shoelace, perpendicular widths, terminal intersections and independent control residuals. Never adjust observations solely to match an expected area.
