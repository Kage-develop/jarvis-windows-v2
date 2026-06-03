# GitHub Upload Checklist

Before publishing this project:

1. Do not upload private local files:
   - `config/api_keys.json`
   - `memory/memory.json`
   - `memory/phone_book.json`
   - `memory/discord_contacts.json`
   - `memory/instagram_contacts.json`
2. Do not upload generated cache files:
   - `__pycache__/`
   - `*.pyc`
   - `.DS_Store`
3. Upload the `.example.json` files instead of private data files.
4. Add a license file if you want other people to reuse or modify the code.
5. After creating the repository, replace `YOUR_USERNAME` in `README.md` with
   your GitHub username.

If an API key was ever pushed to GitHub, revoke it and create a new key.
