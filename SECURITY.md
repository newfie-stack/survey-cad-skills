# Security

Do not post private plans, confidential information or credentials in public issues or pull requests. For sensitive disclosures, contact the repository owner privately using GitHub's private vulnerability reporting feature if enabled.

Crown Plan Agent uses a hash-locked minimal PDF dependency and checks supported
runtime versions before native PDF parsing. Its weekly CI audit must cover every
locked package, including installer tools; dependency-update PRs still require
review and tests. See the dated [runtime and advisory policy](skills/crown-plan-agent/references/dependency-security.md)
for supported versions and unresolved native-library findings. A clean Python
package scan does not clear bundled native libraries or the host operating
system. External reconstruction/CAD/GIS environments require separate review.

These skills are educational guidance, not legal survey certification or a guarantee of compliance or geometric accuracy. Independently verify outputs before professional use.
