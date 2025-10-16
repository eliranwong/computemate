# Online Searches Setup

You can optionally enable online searches with Online Searches MCP server, built in with ComputeMate AI.

Enter `.mcp` in the ComputeMate AI prompt, and remove the `#` symbol at the beginning of the following line:

```
"online": {"command": "python", "args": [os.path.join(COMPUTEMATE_PACKAGE_PATH, "mcp", "online_searches.py")]},
```

## Requirements

The following setup example requires setup of a Gemini API Key (FREE) and Perplexica

Remarks: Read https://github.com/ItzCrazyKns/Perplexica for details about Perplexica.

Setup example:

1. Create a Gemini API Key

Go to https://aistudio.google.com/, log in with a Google account, and create an API key for Free.

2. Download Perplexica, run in terminal:

> git clone https://github.com/ItzCrazyKns/Perplexica.git

3. Navigate to the Perplexica directory:

> cd Perplexica

4. Copy the configuration sample:

> cp sample.config.toml config.toml

5. Edit the configuration file with a text editor, e.g. micro:

> micro config.toml

Fill in your Gemini API key, save it and close the text editor.

<img width="1732" height="1258" alt="Image" src="https://github.com/user-attachments/assets/3944edc8-d4a4-4496-a76b-a334c37e4e02" />

6. Build the Perplexica and Searxng Servers, run in terminal:

> docker compose up -d

<img width="1732" height="1258" alt="Image" src="https://github.com/user-attachments/assets/49a8b986-7b7b-4c88-ac70-a5c69291f37b" />

7. Testing

To test Perplexica web ui, open "http://localhost:3000"

<img width="2560" height="1536" alt="Image" src="https://github.com/user-attachments/assets/e3c10536-ec05-42d2-9ee8-0591023a154d" />

To test Searxng web ui, open "http://localhost:4000"

<img width="2560" height="1536" alt="Image" src="https://github.com/user-attachments/assets/a84c49da-c9e8-4063-985a-fd81dcc21b9d" />

# Integration with ComputeMate AI

With the above setup, you are good to go with the builtin Online Searches MCP server.