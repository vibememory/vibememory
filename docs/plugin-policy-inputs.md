# Operator inputs required for plugin policies

This is a factual decision checklist, not a privacy policy or terms of service. Do not publish it as legal text. The operator or qualified reviewer must confirm the answers before policy pages are drafted and published.

## Privacy decisions

- Which account, connection, memory, document metadata, opaque file, relationship, message, feature-request, audit, and operational log fields are collected?
- For each category, what is its exact purpose and legal basis?
- Which subprocessors or infrastructure providers receive each category, and in which regions?
- What are the retention periods for active data, recoverable archives, backups, logs, and deleted accounts?
- How can a user access, export, correct, or delete data, and what backup delay applies after deletion?
- What security and incident-contact commitments are approved for publication?
- Does analytics or telemetry exist beyond the fixed-cardinality operational metrics implemented in the service?
- How must the policy disclose that `vault_get` returns an explicitly granted secret into the MCP client and model context, where that third party may retain it?

## Terms decisions

- Who is the contracting operator and which contact details and jurisdiction are approved?
- Who may use the hosted service, and are there age or geographic restrictions?
- What acceptable-use, availability, warranty, liability, suspension, termination, and change terms are approved?
- Which terms differ between the hosted service and Apache/MIT-licensed self-hosted components?
- Is there any paid plan, purchase flow, or payment processing? The current submission declaration is none.

After review, publish separate public HTTPS pages on a controlled domain. Each page must identify Vibe Memory and serve the stated purpose without requiring login. Add the verified URLs to `plugin.json`, remove the matching blockers, and run the strict network/package command.
