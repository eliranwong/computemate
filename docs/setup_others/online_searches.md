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

2. Set up Perplexica and SearXNG, run in terminal:

```
sudo apt install -y git
git clone https://github.com/ItzCrazyKns/Perplexica.git
cd Perplexica
docker build -t perplexica .
docker run -d --restart unless-stopped -p 3000:3000 -p 4000:8080 -v perplexica-data:/home/perplexica/data -v perplexica-uploads:/home/perplexica/uploads --name perplexica perplexica
```

3. Testing

To set up providers Perplexica web ui, open "http://localhost:3000"

<img width="2560" height="1536" alt="Image" src="https://github.com/user-attachments/assets/e3c10536-ec05-42d2-9ee8-0591023a154d" />

To test Searxng web ui, open "http://localhost:4000"

<img width="2560" height="1536" alt="Image" src="https://github.com/user-attachments/assets/a84c49da-c9e8-4063-985a-fd81dcc21b9d" />

# Integration with ComputeMate AI

With the above setup, you are good to go with the builtin Online Searches MCP server.