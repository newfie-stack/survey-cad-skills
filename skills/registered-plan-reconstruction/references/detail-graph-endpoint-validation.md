# Enlarged-detail observation graph validation

Before constructing coordinates from an enlarged survey detail, explicitly draw a **source-to-source graph** of monuments, course endpoints and feature membership.

For each printed course:
1. Identify both endpoint symbols directly on the source detail and record their individual source locators.
2. Trace the line carrying the dimension. A nearby dimensioned line belonging to an existing registered R/W must not be attached to the next visually adjacent point on the new subject.
3. Distinguish an inline continuation from a perpendicular tie, and distinguish a lower found post from an open post at an upper deflection.
4. Assign feature ID, side ID and edge role (new subject, existing R/W, tie/control, road/section).
5. Verify the directed bearing, reverse it by 180° only when constructing in the opposite direction, and preserve the original raw text.
6. Cross-check graph adjacency with the full plan and any detail callout before COGO.
7. For a calculated tie to a reference monument, preserve the tie as a separate control edge; do not use it as an acquisition boundary.
8. If the graph's endpoints cannot be proven, keep the observation in the ledger and report REVIEW_REQUIRED. Do not substitute a neighbouring post.

## Synthetic regression
A new subject upper/lower corridor ends at two distinct posts. The lower post has (a) a 28 m eastward continuation to an open post and (b) a 140 m southward existing-R/W control line to a found post. A 76 m tie then connects the found post to a reference iron. The reconstruction must create **two edges from the lower post**, not chain the 140 m course from the 28 m continuation endpoint. A successful DXF audit is insufficient; validate graph adjacency and source feature roles.
