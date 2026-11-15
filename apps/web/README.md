# MailTrace Web

React + TypeScript + Vite frontend for the MailTrace investigation workbench.

## Run locally

```powershell
npm install
npm run dev
```

The API base defaults to `http://localhost:8000/api/v1`. Set `VITE_API_URL` to use another backend URL.

## Validate

```powershell
npm run build
npm test
```

The frontend does not fabricate cases, findings, scores, relationships, or campaigns. Before an investigation exists, views show controlled empty states. If the API is unavailable, intake and relationship views show an explicit unavailable state.