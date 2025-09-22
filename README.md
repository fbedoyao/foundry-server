1. Foundry Setup
Install Foundry: `winget install Microsoft.FoundryLocal`
Install a Foundry model: `foundry model download phi-3.5-mini`

2. Server Setup
Create virtual environment: python -m venv venv
Activate virtual environment: .\venv\Scripts\activate
Install dependencies: pip install -r requirements.txt

3. Starting the Server
python foundry-server.py

If everything is working fine, the logs should show that the Foundry service was started and that the server is running on port 3002
Chat window should now be available to access the "read_graph" tool from the mcp server via natural language
Other tools can be accessible but haven't added them yet.
We can add all of the other tools as well but would still need to define interfaces for each input type.
Also, since this is a very small model, let's not overwhelm it with big graphs
I'm attaching a small example below that works!
NOTE: MCP Server should also be running.

SAMPLE memory.json IN THE MCP SERVER:
{"type":"entity","name":"source.py","entityType":"FILE","observations":["Contains the function calculate_tax()","Defines a global variable tax_rate with a hardcoded value of 0.25","Serves as the main tax calculation module"]}
{"type":"entity","name":"calculate_tax()","entityType":"FUNCTION","observations":["Defined in source.py","Takes income as a parameter","Uses the global variable tax_rate to compute tax","Returns the calculated tax amount"]}
{"type":"entity","name":"income","entityType":"PARAMETER","observations":["Parameter to calculate_tax() function","Represents the income on which tax is calculated"]}
{"type":"entity","name":"tax_rate","entityType":"GLOBAL_VARIABLE","observations":["Defined at the module level in source.py","Holds the tax rate used by calculate_tax()","Has a hardcoded value of 0.25"]}
{"type":"entity","name":"0.25","entityType":"LITERAL_VALUE","observations":["Literal value assigned to tax_rate","Represents the hardcoded tax rate"]}
{"type":"entity","entityType":"CONCLUSION","name":"Tax calculation is hardcoded","observations":["Tax calculation is hardcoded","Derived from tax_rate --HAS_VALUE--> 0.25"]}
{"type":"entity","entityType":"CONCLUSION","name":"Function depends on global state","observations":["Function depends on global state","Derived from calculate_tax() --USES--> tax_rate [Global]"]}
{"type":"relation","from":"source.py","relationType":"CONTAINS_FUNCTION","to":"calculate_tax()"}
{"type":"relation","from":"source.py","relationType":"CONTAINS_GLOBAL_VARIABLE","to":"tax_rate"}
{"type":"relation","from":"calculate_tax()","relationType":"TAKES_PARAM","to":"income"}
{"type":"relation","from":"calculate_tax()","relationType":"USES","to":"tax_rate"}
{"type":"relation","from":"tax_rate","relationType":"HAS_VALUE","to":"0.25"}
{"type":"relation","from":"Tax calculation is hardcoded","relationType":"DERIVED_FROM","to":"tax_rate"}
{"type":"relation","from":"Function depends on global state","relationType":"DERIVED_FROM","to":"calculate_tax()"}
{"type":"relation","from":"Function depends on global state","relationType":"DERIVED_FROM","to":"tax_rate"}

SAMPLE RESPONSE TO PROMPT: "summarize the knowledge graph"
The knowledge graph summarizes a Python module 'source.py' containing a 'calculate_tax()' function that performs tax calculations using a hardcoded tax rate of '0.25'. The function depends on the global state, specifically the 'tax_rate`

4. Exit the virtual environment
- Stop the server with ctrl+c
- Run `deactivate`