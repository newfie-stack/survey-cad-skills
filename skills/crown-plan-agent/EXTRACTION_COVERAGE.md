# PDF extraction contract and coverage

The adapter provides bounded evidence inventory. It does not reconstruct ground survey geometry, recognize every visual object, or certify the drawing. The CLI requests text inventory only; callers may separately request straight-stroke and Bézier inventory.

| Input or feature | Implemented result | Verification or boundary |
|---|---|---|
| Native PDF text | Text, page, PDF-point box and baseline direction | Synthetic span and PDF integration tests; original text remains a candidate observation |
| Sheet rotation | Unrotated, crop-relative coordinates | 0/90/180/270-degree synthetic sheets |
| Nonzero crop origin | Coordinates remain relative to the visible crop | Generated cropped-page cases |
| PDF UserUnit | Page dimensions match the extracted point space | Generated scaled/rotated-page cases |
| Partially clipped span | Visible box bounded to the page; original box retained | Edge-clipping tests preserve `original_bbox_points` |
| Malformed or wholly outside box | Explicit error rather than invented coordinates | Nonfinite, reversed and out-of-page cases |
| Straight vector strokes | Unclassified `PDF_LINE` endpoints and stroke width | API inventory tests; never surveyed boundary identity |
| Cubic Bézier strokes | Unclassified control-point inventory | Curve tests and cumulative resource limits; never interpreted as a cadastral circular arc |
| Label/line proximity, direction, leaders | Ranked review candidates | Synthetic association/orientation/leader tests; ambiguity remains unresolved |
| Full-span plan heading and description | Candidate proposed plan type | Invented heading tests, including `Plan of Survey Showing ...`; not statutory classification |
| Numerical scale | Candidate ratio and provenance | Main/detail/access context still requires review; an access-map ratio can match |
| Total-area text or supported split table | Hectare candidate or explicit ambiguity | Competing text/table totals share one document-wide ambiguity gate |
| Scanned, outlined, fragmented or damaged OCR text | May remain unknown | No OCR or reliable multi-span heading reconstruction is claimed |
| Rectangles, hatches, symbols, arrowheads | Visual review or unresolved role | No semantic recognition acceptance is claimed |
| Survey area/closure | Separate explicit-coordinate input only | PDF point geometry is not accepted as surveyed metric coordinates |
| Output records | Exclusive creation; no overwrite of an existing inventory/report | Synthetic CLI and inventory-write cases |

## Resource boundaries

The default adapter limits are 100 pages, 100 MB and 200,000 text spans. Straight vectors and Bézier curves have separately enforced caps based on the supplied span limit; the curve cap is cumulative across pages. Positive integer limit validation, encrypted-input rejection and limit-exceeded behavior are tested. These bounds do not constitute a hostile-file sandbox or a complexity guarantee for downstream span/vector ranking.

## Evidence and acceptance

The reviewed source/test snapshot is identified in [TECHNICAL_REVIEW.md](TECHNICAL_REVIEW.md). The full suite, compilation, standalone smoke example and private-branch CI have passed for the reviewed code. [Anonymized development results](VALIDATION_RESULTS.md) document additional real-input exercises and their limits. Source plans, source images and extracted project inventories are not bundled.

This contract accepts the implemented inventory and conservative review behavior. Unresolved visual/semantic cases remain visible to the reviewer; they are not automatically treated as missing drawing elements or noncompliance.
