{
    # Check configuration format at https://gofastmcp.com/clients/client#configuration-format
    #
    # Example - Online Search Utilities; Perplexica setup is required; read https://github.com/eliranwong/computemate/blob/main/docs/setup_others/online_searches.md
    # Uncomment the following line to use it, i.e. remove the `#` symbol
    #"online": {"command": "python", "args": [os.path.join(COMPUTEMATE_PACKAGE_PATH, "mcp", "online_searches.py")]},
    #
    # Example - Youtube Utilities; Installation of `ffmpeg` is required; read https://github.com/eliranwong/computemate/blob/main/docs/setup_others/ffmpeg.md
    # Uncomment the following line to use it, i.e. remove the `#` symbol
    #"youtube": {"command": "python", "args": [os.path.join(COMPUTEMATE_PACKAGE_PATH, "mcp", "youtube.py")]},
    #
    # Example - GitHub MCP
    # Export your GITHUB_TOKEN, e.g. `export GITHUB_TOKEN=xxxxxxxxxxxxxx`
    # Uncomment the following 4 lines to use it
    #"github": {
    #    "url": "https://api.githubcopilot.com/mcp",
    #    "headers": {"Authorization": os.getenv("GITHUB_TOKEN")},
    #},
}