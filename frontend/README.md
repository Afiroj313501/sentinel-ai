# Sentinel AI frontend

The frontend is a Vite-powered React and TypeScript application. It expects the
backend API to be available at `http://localhost:8000` during local development.

From this directory:

```powershell
npm install
npm run dev
```

The available validation commands are:

```powershell
npm run build
npm run lint
```

`npm run build` type-checks the application and creates the production bundle.
`npm run lint` runs Oxlint with the repository's checked-in configuration.
