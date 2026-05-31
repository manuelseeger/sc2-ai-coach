---
name: improve-frontend
description: Use this to imrpove the frontend of our webapp based on the user input.
disable-model-invocation: true
---
# Startup
Start the API server with 
`uv run uvicorn src.api.app:app --host 127.0.0.1 --port 6789 --reload`

If the port is in use, backend might already be running. See if you can already access the frontend. 

http://127.0.0.1:6789 will serve the frontend with no caching. Just rebuild the webapp after you made changes to see the changes in the frontend.

## Testing 

Open the app using `playwright skill` to inspect. Always run playwright with --headed so that the user can follow your actions.

When saving files using playwright, for example when you take screenshots, put them into the `.playwright-cli/` folder in the root of the project. 

## Guidelines

For all changes, consider whether they can be made globally in the app in components or global stylesheet. Try to keep individual changes on views minimal if possible. Don't be afraid to refactor the frontend. 

See if you can identify components that can be reused across the app. Extract these to reusable components. DRY.

Same with TypeScript types and code. Try to keep the code DRY and reusable.

## Style

Use global styles and variables as much as possible. Keep the styling consistent across the app. 

Have a look at the examples mentioned in [./docs/spec/webapp.md](./docs/spec/webapp.md) for styling and design guidelines.

## Scope

Improve the frontend. Don't touch the backend.
