# Security

## Repository data policy

This portfolio repository must contain only synthetic examples and sanitized workflow exports. Do not commit:

- Telegram bot tokens or user identifiers;
- Google OAuth secrets, spreadsheet IDs, Drive folder IDs, or live file links;
- OpenAI API keys;
- n8n credential exports or production workflow backups;
- customer messages, supplier contacts, prices, or other private business records;
- `.env` files, databases, logs, caches, or generated runtime data.

Use `.env.example` only as a placeholder reference. Configure real credentials in the relevant secret store or in n8n's credential manager.

## Runtime boundary

The HTTP service has no authentication and is bound to `127.0.0.1` by the supplied Compose file. Keep it local or on a restricted Docker network unless authentication and transport security are added.

Before activating the Telegram trigger, set its `Restrict to User IDs` field to the authorized operator's numeric ID.

## Reporting a problem

If a secret is accidentally committed, revoke it first, remove it from Git history, and replace any affected credentials before continuing development.
